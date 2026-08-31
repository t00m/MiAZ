#!/usr/bin/python3

"""UI: the keyboard shortcuts window, on both libadwaita paths.

Adw.ShortcutsDialog arrived in libadwaita 1.8. Debian 13, the current stable,
ships 1.7.6, so show_app_help builds the same list out of older parts there.
The fallback is the path a developer on Fedora never sees, so both are built
here whatever this machine runs.
"""

from gi.repository import Adw
from gi.repository import Gtk

from MiAZ.frontend.desktop.services.actions import accelerator_label


def sections(driver):
    return driver.service('actions').shortcut_sections()


def titles(sections_):
    """Every shortcut label, flattened, in order."""
    return [label for _title, rows in sections_ for label, _accel in rows]


def descendants(widget):
    """Walk the widget tree.

    An Adw.Dialog keeps its content behind get_child() rather than in the
    widget child list, so walking the dialog itself finds nothing at all until
    it is presented. Start from the child it holds.
    """
    if isinstance(widget, Adw.Dialog):
        widget = widget.get_child()
        if widget is None:
            return
    child = widget.get_first_child()
    while child is not None:
        yield child
        yield from descendants(child)
        child = child.get_next_sibling()


def labels_in(widget):
    return {child.get_text() for child in descendants(widget)
            if isinstance(child, Gtk.Label) and child.get_text()}


def test_the_accelerator_is_rendered_the_way_a_user_reads_it():
    """How GTK spells a key is GTK's business, and it changes between versions:
    4.18 writes 'Ctrl+BackSpace' where 4.22 writes 'Ctrl+Backspace'. What MiAZ
    guarantees is that the raw accelerator never reaches the user.
    """
    for accelerator in ('<Control>s', '<Control>BackSpace', '<Control>question'):
        label = accelerator_label(accelerator)
        assert '<' not in label and '>' not in label, label
        assert label.lower().startswith('ctrl+'), label
    assert accelerator_label('F1') == 'F1'


def test_an_unparsable_accelerator_is_shown_as_written():
    """Better a raw string than an empty cell: the row still says a key exists."""
    assert accelerator_label('not-an-accelerator') == 'not-an-accelerator'


def test_the_fallback_lists_every_shortcut(clean_view):
    """The path Debian 13 takes. Built directly, so it is exercised on a
    machine whose libadwaita would otherwise never reach it.
    """
    actions = clean_view.service('actions')
    dialog = actions._build_shortcuts_fallback(sections(clean_view))
    try:
        shown = labels_in(dialog)
        for title in titles(sections(clean_view)):
            assert title in shown, f"{title!r} missing from the fallback"
        # And the keys next to them, not just the names.
        assert 'Ctrl+S' in shown
        assert 'F1' in shown
    finally:
        dialog.close()


def test_the_fallback_uses_no_deprecated_shortcuts_widget(clean_view):
    """Gtk.ShortcutsWindow and Gtk.ShortcutLabel are deprecated as of GTK 4.18
    and are what MiAZ moved away from. The fallback must not reintroduce them.
    """
    actions = clean_view.service('actions')
    dialog = actions._build_shortcuts_fallback(sections(clean_view))
    try:
        for child in descendants(dialog):
            assert not isinstance(child, (Gtk.ShortcutsWindow, Gtk.ShortcutLabel)), (
                f"the fallback builds a deprecated {type(child).__name__}")
    finally:
        dialog.close()


def test_both_builders_show_the_same_shortcuts(clean_view):
    """The two paths read one list, so they cannot describe different keys."""
    actions = clean_view.service('actions')
    if (Adw.MAJOR_VERSION, Adw.MINOR_VERSION) < (1, 8):
        import pytest
        pytest.skip('libadwaita is older than 1.8, the native dialog does not exist')
    native = actions._build_shortcuts_dialog(sections(clean_view))
    fallback = actions._build_shortcuts_fallback(sections(clean_view))
    try:
        wanted = set(titles(sections(clean_view)))
        assert wanted <= labels_in(native)
        assert wanted <= labels_in(fallback)
    finally:
        native.close()
        fallback.close()
