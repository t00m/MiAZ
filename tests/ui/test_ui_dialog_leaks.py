#!/usr/bin/python3

"""UI: dialogs must not leave handlers on long-lived objects.

A mass-rename dialog connects to its field config's 'used-updated' so the
dropdown follows a value added while the dialog is open. The config outlives
the dialog, so that handler has to come off again however the dialog is
dismissed.

Adw.AlertDialog emits 'response' on every dismissal, including Escape and
close(), which is what makes a single 'response' handler enough. These tests
exist to keep it that way: a dialog moved to a class that does not emit
'response' when it is dismissed would start leaking, and nothing else would
notice.

Dismiss by clicking a real button. A synthetic emit('response') is not the same
thing, because Adw.AlertDialog closes itself from its own button handler and
emits 'closed' first; a bare emit skips all of that and tests nothing real.
"""

import pytest

from gi.repository import Gtk

from MiAZ.backend.models import Country

from tests.ui.test_ui_plugin_signals import count_handlers

DOCUMENTS = ('20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf',
             '20260505-ES-HOU-ACME-INV-electricity-JOHNDOE.pdf')


def click_response(dialog, label):
    """Click a real response button, as a user would."""
    def walk(widget):
        yield widget
        child = widget.get_first_child() if hasattr(widget, 'get_first_child') else None
        while child is not None:
            yield from walk(child)
            child = child.get_next_sibling()
    for widget in walk(dialog):
        if isinstance(widget, Gtk.Button) and widget.get_label() == label:
            widget.emit('clicked')
            return True
    return False


def open_mass_rename(driver, monkeypatch):
    """Open the Country mass-rename dialog and hand back its dialog object.

    The dialogs service is not asked to register this one as a named widget, so
    the dialog is captured as show_action hands it over.
    """
    driver.select_documents(*DOCUMENTS)
    driver.pump(0.3)

    srvdlg = driver.service('dialogs')
    captured = []
    real_show_action = srvdlg.show_action

    def spy(*args, **kwargs):
        dialog = real_show_action(*args, **kwargs)
        captured.append(dialog)
        return dialog

    monkeypatch.setattr(srvdlg, 'show_action', spy)
    driver.service('massrename').rename_field(None, None, Country)
    driver.pump(0.4)
    monkeypatch.undo()
    assert captured, 'the mass-rename dialog was never created'
    return captured[-1]


@pytest.mark.parametrize('dismiss', ['response', 'close'])
def test_mass_rename_leaves_no_handler_on_the_config(clean_view, monkeypatch, dismiss):
    """'response' clicks the Cancel button, 'close' dismisses the dialog."""
    config = clean_view.app.get_config('Country')
    before = count_handlers(config, 'used-updated')

    dialog = open_mass_rename(clean_view, monkeypatch)
    during = count_handlers(config, 'used-updated')
    assert during == before + 1, 'the dialog did not connect what this test tracks'

    if dismiss == 'response':
        assert click_response(dialog, 'Cancel'), 'no Cancel button on the dialog'
    else:
        dialog.close()
    clean_view.pump(0.4)

    try:
        after = count_handlers(config, 'used-updated')
        assert after == before, (
            f"dismissing with '{dismiss}' left {after - before} handler(s) "
            f"on the Country config")
    finally:
        # Harmless when the click already closed it, and it keeps a failed
        # assertion from leaving a dialog sitting over the next test.
        dialog.close()
        clean_view.pump(0.3)


def test_two_mass_renames_do_not_stack_handlers(clean_view, monkeypatch):
    """The count has to come back to the same number every time, not creep."""
    config = clean_view.app.get_config('Country')
    before = count_handlers(config, 'used-updated')
    for _round in range(3):
        dialog = open_mass_rename(clean_view, monkeypatch)
        dialog.close()
        clean_view.pump(0.3)
    assert count_handlers(config, 'used-updated') == before


RENAME_DOC = '20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf'


def test_reopening_the_rename_dialog_does_not_stack_handlers(clean_view):
    """MiAZRenameDialog connects five config signals and one on the repository.

    Those objects outlive the dialog, and a new dialog is built every time a
    document is renamed, so without dispose() the counts grew by six per open.
    """
    configs = [clean_view.app.get_config(name)
               for name in ('Country', 'Group', 'SentBy', 'Purpose', 'SentTo')]
    repository = clean_view.service('repo')

    def census():
        return ([count_handlers(c, 'used-updated') for c in configs]
                + [count_handlers(repository, 'repository-switched')])

    actions = clean_view.service('actions')

    actions._document_rename_single(RENAME_DOC)
    clean_view.wait_until(lambda: clean_view.widget('dialog-rename') is not None,
                          message='the rename dialog')
    clean_view.pump(0.3)
    baseline = census()
    clean_view.widget('dialog-rename').emit('response', 'cancel')
    clean_view.pump(0.3)

    for _round in range(3):
        actions._document_rename_single(RENAME_DOC)
        clean_view.pump(0.4)
        assert census() == baseline, 'handlers stacked across rename dialogs'
        clean_view.widget('dialog-rename').emit('response', 'cancel')
        clean_view.pump(0.3)
