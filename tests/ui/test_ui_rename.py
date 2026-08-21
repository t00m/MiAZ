#!/usr/bin/python3

"""UI: the rename dialog. Checklist sections 4 and 11."""

import os
import pytest

from gi.repository import GLib
from gi.repository import Gtk

from MiAZ.backend.util import UNKNOWN_DATE

DOCUMENT = '20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf'
# Its sender is not in the configuration, which is what makes the dialog open
# invalid, as it does for a real document that needs review.
UNKNOWN_DOCUMENT = '20260401-ES-FIN-STRANGER-INV-unknown-JOHNDOE.pdf'


@pytest.fixture
def rename_dialog(clean_view):
    """Open the real rename dialog, and close it however the test ends."""
    actions = clean_view.service('actions')
    actions._document_rename_single(DOCUMENT)
    clean_view.wait_until(lambda: clean_view.widget('dialog-rename') is not None,
                          message='the rename dialog')
    dialog = clean_view.widget('dialog-rename')
    widget = clean_view.widget('rename-widget')
    clean_view.pump(0.3)
    yield clean_view, dialog, widget
    dialog.emit('response', 'cancel')
    clean_view.pump(0.3)


def rename_button(dialog):
    return dialog._buttons['apply']


def test_the_dialog_opens_with_the_fields_filled(rename_dialog):
    """4.1."""
    _driver, _dialog, widget = rename_dialog
    assert widget.entry_date.get_text() == '20260612'
    assert widget.entry_concept.get_text().upper().startswith('MORTGAGE')


def test_rename_is_insensitive_while_values_are_unknown(clean_view):
    """4.2: an unknown sender leaves that dropdown on Any, so the name cannot
    be built and the button must not pretend otherwise."""
    actions = clean_view.service('actions')
    actions._document_rename_single(UNKNOWN_DOCUMENT)
    clean_view.wait_until(
        lambda: clean_view.widget('dialog-rename') is not None,
        message='the rename dialog')
    dialog = clean_view.widget('dialog-rename')
    widget = clean_view.widget('rename-widget')
    clean_view.pump(0.4)
    try:
        assert widget.is_valid() is False
        assert rename_button(dialog).get_sensitive() is False
    finally:
        dialog.emit('response', 'cancel')
        clean_view.pump(0.3)


def test_rename_becomes_sensitive_once_the_fields_are_valid(rename_dialog):
    """4.3."""
    driver, dialog, widget = rename_dialog
    fill_required(driver, widget)
    assert widget.is_valid() is True
    assert rename_button(dialog).get_sensitive() is True


def test_rename_goes_insensitive_again_when_the_concept_is_cleared(rename_dialog):
    """4.4."""
    driver, dialog, widget = rename_dialog
    fill_required(driver, widget)
    widget.entry_concept.set_text('')
    driver.pump(0.3)
    assert rename_button(dialog).get_sensitive() is False


def test_group_and_purpose_do_not_block(rename_dialog):
    """4.5: they are advisory, and the button must not wait for them."""
    driver, dialog, widget = rename_dialog
    fill_required(driver, widget)
    widget.dpdGroup.set_selected(0)
    widget.dpdPurpose.set_selected(0)
    driver.pump(0.3)
    assert rename_button(dialog).get_sensitive() is True


def test_the_preview_follows_the_fields(rename_dialog):
    """4.10."""
    driver, _dialog, widget = rename_dialog
    widget.entry_concept.set_text('somethingelse')
    driver.pump(0.3)
    assert 'SOMETHINGELSE' in widget.lblFilenameNew.get_text().upper()


def test_the_suggest_button_needs_two_characters(rename_dialog):
    """4.18."""
    driver, _dialog, widget = rename_dialog
    button = driver.widget('rename-button-suggest')
    if button is None:
        pytest.skip('the Suggest button is not registered under a widget name')
    widget.entry_concept.set_text('a')
    driver.pump(0.3)
    assert button.get_sensitive() is False
    widget.entry_concept.set_text('ab')
    driver.pump(0.3)
    assert button.get_sensitive() is True


def test_cancel_writes_nothing(rename_dialog, sandbox):
    """4.16."""
    import os
    driver, dialog, widget = rename_dialog
    fill_required(driver, widget)
    widget.entry_concept.set_text('cancelled')
    driver.pump(0.2)
    dialog.emit('response', 'cancel')
    driver.pump(0.4)
    assert os.path.exists(os.path.join(sandbox['Alpha'], DOCUMENT))


def fill_required(driver, widget):
    """Set the five fields that block a rename, as a user would."""
    widget.entry_date.set_text('20260612')
    for dropdown in (widget.dpdCountry, widget.dpdSentBy, widget.dpdSentTo):
        pick_first_real_value(dropdown)
    widget.entry_concept.set_text('mortgage')
    driver.pump(0.4)


def pick_first_real_value(dropdown):
    model = dropdown.get_model()
    for position in range(len(model)):
        if model.get_item(position).id != 'Any':
            dropdown.set_selected(position)
            return
    raise AssertionError('the dropdown offers no real value')


# ---------------------------------------------------------------------------
# 4.6: the date field
# ---------------------------------------------------------------------------

def leave_date_field(driver, widget):
    """Move the focus off the date entry, which is when the verdict is shown."""
    widget.entry_concept.grab_focus()
    driver.pump(0.3)


def test_an_impossible_date_is_refused_and_kept(rename_dialog):
    """4.6: 20261301 has no month 13.

    Refused means the field keeps what was typed, so the user can see and fix
    it, and Rename stays insensitive. Replacing it with a valid date is the
    one thing that must not happen: the dialog would then be ready to rename
    the document to a date nobody chose.
    """
    driver, dialog, widget = rename_dialog

    widget.entry_date.grab_focus()
    widget.entry_date.set_text('20261301')
    driver.pump(0.4)

    assert widget.entry_date.get_text() == '20261301'
    assert widget.has_valid_date() is False
    assert rename_button(dialog).get_sensitive() is False

    leave_date_field(driver, widget)
    # Nothing next to the field may still read as a real date.
    assert 'not a date' in widget.label_date.get_text()


def test_a_valid_date_typed_by_hand_is_accepted(rename_dialog):
    driver, dialog, widget = rename_dialog

    widget.entry_date.grab_focus()
    widget.entry_date.set_text('20260301')
    driver.pump(0.4)

    assert widget.entry_date.get_text() == '20260301'
    assert rename_button(dialog).get_sensitive() is True

    leave_date_field(driver, widget)
    # The document opens on 20260612, so a label that merely contains '2026'
    # would pass without the field ever having been read.
    assert widget.label_date.get_text() == 'Sunday, March 01 2026'


def test_the_date_is_not_judged_while_it_is_being_typed(rename_dialog):
    """A date is typed one digit at a time and is wrong for most of them. The
    label used to follow every keystroke, so it flickered through readings the
    user never asked for."""
    driver, dialog, widget = rename_dialog

    widget.entry_date.set_text('20260301')
    driver.pump(0.3)
    leave_date_field(driver, widget)
    settled = widget.label_date.get_text()
    assert '2026' in settled

    widget.entry_date.grab_focus()
    for text in ('2026030', '202603', '20260', '2026'):
        widget.entry_date.set_text(text)
        driver.pump(0.15)
        assert widget.label_date.get_text() == settled, (
            f"the label moved while '{text}' was on its way in")


def test_leaving_the_date_field_shows_the_verdict(rename_dialog):
    """The other half of the same rule: once the user is done with the field,
    they have to be told."""
    driver, dialog, widget = rename_dialog

    widget.entry_date.grab_focus()
    widget.entry_date.set_text('2026')
    driver.pump(0.3)

    leave_date_field(driver, widget)
    assert 'not a date' in widget.label_date.get_text()


def test_applying_with_a_half_typed_date_is_refused(rename_dialog):
    """Ctrl+Enter applies from any field, including one still being typed in,
    so apply is the other moment the date has to be checked."""
    driver, dialog, widget = rename_dialog

    widget.entry_date.grab_focus()
    widget.entry_date.set_text('202613')
    driver.pump(0.3)

    dialog.emit('response', 'apply')
    driver.pump(0.4)

    assert widget.entry_date.get_text() == '202613', 'the date was completed'
    assert 'not a date' in widget.label_date.get_text()


def test_a_half_typed_date_does_not_become_a_real_one(rename_dialog):
    """Typing goes through incomplete states. None of them may be completed
    for the user: '2026' is not 2026-01-01."""
    driver, dialog, widget = rename_dialog

    for text in ('2', '20', '202', '2026', '20261', '202613'):
        widget.entry_date.set_text(text)
        driver.pump(0.15)
        assert widget.entry_date.get_text() == text


# ---------------------------------------------------------------------------
# 4.9: the manage button next to a restricted field
# ---------------------------------------------------------------------------

def open_manage(driver, widget, button):
    """Click a field's manage button and return the window it opens."""
    driver.app.add_widget('dialog-manage-resource', None)
    button.emit('clicked')
    driver.wait_until(
        lambda: driver.widget('dialog-manage-resource') is not None,
        message='the manage window')
    driver.pump(0.3)
    return driver.widget('dialog-manage-resource')


def test_the_manage_window_is_populated_every_time(rename_dialog):
    """4.9: it used to come up empty from the second click on.

    The selector was built once, when the button was connected, and the first
    window took ownership of it. The second window packed a widget that was
    already spoken for, so it showed nothing until the rename dialog itself
    was closed and rebuilt.
    """
    driver, _dialog, widget = rename_dialog

    for attempt in ('first', 'second'):
        window = open_manage(driver, widget, widget.btnCountry)
        # The window holds the configuration view: it must have rows both times.
        views = [child for child in _walk(window) if hasattr(child, 'get_config_for')]
        assert views, f'{attempt} opening has no configuration view'
        view = views[0]
        assert len(view.viewSl.get_model_filter()) > 0, \
            f'{attempt} opening shows an empty list'
        window.close()
        driver.pump(0.3)


def _walk(widget):
    """Every widget under this one, itself included."""
    yield widget
    child = widget.get_first_child() if hasattr(widget, 'get_first_child') else None
    while child is not None:
        yield from _walk(child)
        child = child.get_next_sibling()


# ---------------------------------------------------------------------------
# Detect date (checklist 4.7b, 4.7c). Triggered through the dialog's grouped
# 'Detect' menu button (services/actions.py); called directly here since the
# menu itself is built and owned by MiAZActions, not this widget.
# ---------------------------------------------------------------------------

def test_detect_reads_the_date_out_of_the_concept(rename_dialog):
    """4.7b: the date can be asked for at any point, not only when the document
    arrives without one. Here the field already holds a date and detect must
    still replace it."""
    driver, _dialog, widget = rename_dialog
    assert widget.entry_date.get_text() == '20260612'
    widget.entry_concept.set_text('FACTURA_15_03_2024')
    driver.pump(0.3)
    widget.detect_date()
    driver.pump(0.3)
    assert widget.entry_date.get_text() == '20240315'


def test_detect_reads_the_concept_as_it_stands_now(rename_dialog):
    """4.7c: the concept is where the original filename is kept, and the user
    may have just corrected it. Detect must read the entry, not the name the
    file still has on disk."""
    driver, _dialog, widget = rename_dialog
    widget.entry_concept.set_text('IMG20231114093000')
    driver.pump(0.3)
    widget.detect_date()
    driver.pump(0.3)
    assert widget.entry_date.get_text() == '20231114'


def test_detect_says_it_does_not_know_rather_than_guessing(rename_dialog):
    """No date in the concept and none in the file metadata. The old code
    answered with the file mtime, which for a document imported today read as
    today; the answer now is the unknown date."""
    driver, _dialog, widget = rename_dialog
    widget.entry_concept.set_text('MORTGAGE')
    driver.pump(0.3)
    widget.detect_date()
    driver.pump(0.3)
    assert widget.entry_date.get_text() == UNKNOWN_DATE
    # It is still a valid date, so the rename is not blocked by it.
    assert widget.validate_date(UNKNOWN_DATE) is True


def test_detect_declines_an_ambiguous_date(rename_dialog):
    """03/04/2024 is 3 April or 4 March depending on where the document came
    from, and the name does not say. Reporting the unknown date is right; both
    readings would be wrong half the time."""
    driver, _dialog, widget = rename_dialog
    widget.entry_concept.set_text('FACTURA_03_04_2024')
    driver.pump(0.3)
    widget.detect_date()
    driver.pump(0.3)
    assert widget.entry_date.get_text() == UNKNOWN_DATE


def test_detect_reads_the_date_out_of_the_pdf_metadata(rename_dialog):
    """4.7d: the concept holds an invoice number, so the answer has to come from
    the document's own metadata. This is the case that was silently broken: the
    PDF probe sat behind `except ImportError` on a library MiAZ does not depend
    on, so it never ran and the date fell through to the file mtime."""
    driver, _dialog, widget = rename_dialog
    repository = driver.service('repo')
    path = os.path.join(repository.docs, DOCUMENT)
    with open(path, 'rb') as handler:
        original = handler.read()
    try:
        with open(path, 'wb') as handler:
            handler.write(b"%PDF-1.4\n<< /Title (invoice) "
                          b"/CreationDate (D:20250116042015+01'00') >>\n%%EOF\n")
        widget.entry_concept.set_text('RG151038433387')
        driver.pump(0.3)
        widget.detect_date()
        driver.pump(0.3)
        assert widget.entry_date.get_text() == '20250116'
    finally:
        with open(path, 'wb') as handler:
            handler.write(original)
        driver.pump(0.3)


# ---------------------------------------------------------------------------
# The header page selector
# ---------------------------------------------------------------------------

def menu_labels(menu):
    return [menu.get_item_attribute_value(i, 'label', None).get_string()
            for i in range(menu.get_n_items())]


def test_the_pages_are_a_menu_not_a_row_of_tabs(rename_dialog):
    """Adw.ViewSwitcher put one tab in the header per page, so every plugin
    that contributed one made the dialog wider. A menu grows downwards."""
    _driver, dialog, widget = rename_dialog
    selector = widget.get_switcher()
    assert selector is not None, 'no page selector with plugin tabs registered'
    assert isinstance(selector, Gtk.MenuButton), type(selector).__name__

    def walk(w):
        child = w.get_first_child()
        while child is not None:
            yield child
            yield from walk(child)
            child = child.get_next_sibling()
    assert not any(type(w).__name__ == 'AdwViewSwitcherButton'
                   for w in walk(dialog.headerbar)), 'the tab row is still there'


def test_fields_comes_first_then_the_plugin_pages(rename_dialog):
    _driver, _dialog, widget = rename_dialog
    labels = menu_labels(widget.get_switcher().get_menu_model())
    assert labels[0] == 'Fields', labels
    assert len(labels) == 1 + len(widget.plugin_tabs), labels


def test_choosing_a_page_switches_the_stack(rename_dialog):
    driver, _dialog, widget = rename_dialog
    name = widget.plugin_tabs[0][0]
    widget._page_action.activate(GLib.Variant('s', name))
    driver.pump(0.3)
    assert widget.stack.get_visible_child_name() == name


def test_the_button_follows_the_stack_however_the_page_changed(rename_dialog):
    """A plugin focuses its own tab when it refuses a rename, without going
    near the menu. The button has to say where the user actually is."""
    driver, _dialog, widget = rename_dialog
    name, _tab = widget.plugin_tabs[0]
    widget.stack.set_visible_child_name(name)
    driver.pump(0.3)
    assert widget._page_label.get_text() != 'Fields'

    widget.stack.set_visible_child_name('fields')
    driver.pump(0.3)
    assert widget._page_label.get_text() == 'Fields'
