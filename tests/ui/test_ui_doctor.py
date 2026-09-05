#!/usr/bin/python3

"""UI: the Doctor report's Show button, through the real plugin.

The workspace side is covered in test_ui_widgets.py. This drives the plugin
itself: the report is built from the sandbox repository, the dialog is the one
the user sees, and the button is clicked rather than the method called. That is
where the bug was, so that is what is tested.
"""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

import pytest


def buttons(widget, found=None):
    """Every Gtk.Button under a widget, depth first."""
    found = [] if found is None else found
    child = widget.get_first_child() if hasattr(widget, 'get_first_child') else None
    while child is not None:
        if isinstance(child, Gtk.Button):
            found.append(child)
        buttons(child, found)
        child = child.get_next_sibling()
    return found


@pytest.fixture
def doctor(miaz):
    """The Doctor plugin, loaded for the test and left as it was found."""
    system = miaz.service('plugin-system')
    info = system.get_plugin_info('doctor')
    assert info is not None, 'the Doctor plugin is not in the index'
    was_loaded = system.is_plugin_loaded(info)
    if not was_loaded:
        assert system.load_plugin(info), 'the Doctor plugin did not load'
    miaz.pump(0.5)
    instance = system.get_extension('doctor')
    assert instance is not None, 'the Doctor plugin has no extension instance'
    yield instance
    if not was_loaded:
        system.unload_plugin(info)
        miaz.pump(0.3)


def test_every_show_button_puts_its_documents_on_screen(clean_view, doctor):
    """Show is the whole point of the report: a finding nobody can look at is
    half a finding. Every button is clicked, because they broke together.

    The filters are narrowed to something that excludes the findings first.
    With Review on and a search in the box, every Show showed an empty
    workspace: Review asks for pending documents while an explicit list lifts
    the pending check, and the two together match nothing.
    """
    workspace = clean_view.workspace
    review = clean_view.widget('workspace-togglebutton-pending-docs')
    search = clean_view.widget('searchentry')

    report = doctor.examine()
    findings = [finding for finding in report if finding.documents]
    assert findings, 'the sandbox repository is too healthy to test with'

    try:
        for index, finding in enumerate(findings):
            search.set_text('nothing matches this')
            review.set_active(True)
            clean_view.pump(0.5)

            doctor._on_examined(report)
            clean_view.pump(0.5)
            dialog = clean_view.widget('doctor-dialog')
            assert dialog is not None, 'the report dialog was not built'
            shows = [button for button in buttons(dialog)
                     if button.get_label() == 'Show']
            assert len(shows) == len(findings), 'one Show per finding with documents'

            shows[index].emit('clicked')
            clean_view.wait_until(
                lambda: sorted(clean_view.displayed()) == sorted(finding.documents),
                message=f'the documents {finding.check} named')
            assert workspace.get_shown_documents() == frozenset(finding.documents)
            workspace.clear_documents()
            clean_view.pump(0.5)
    finally:
        review.set_active(False)
        search.set_text('')
        workspace.clear_documents()
        clean_view.pump(0.5)
