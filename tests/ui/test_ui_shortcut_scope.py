#!/usr/bin/python3

"""UI: the five bare keys fire on the document list and nowhere else.

Return, F2, Delete and Ctrl+A are what every file manager uses and what every
text entry also wants. MiAZ has a search entry that can hold focus, so a
global Delete would remove documents while somebody was editing a filter.
Escape joins them for a different reason: app.set_accels_for_action installs
a capture phase controller on the window, and capture runs before the bubble
phase handler that Adw.AlertDialog, Adw.Dialog and Gtk.Popover use to close
themselves on Escape. A global Escape would stop those dialogs from closing.
All five are installed on the list instead, and this file is the proof.
"""

from gi.repository import Adw
from gi.repository import Gtk

from MiAZ.frontend.desktop.services import shortcuts as sct

DELETE_DOC = '20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf'


def controller(driver):
    found = driver.widget('workspace-shortcut-controller')
    assert found is not None, 'the document list has no shortcut controller'
    return found


def test_the_list_controller_is_local_scope(miaz):
    """GLOBAL would put these keys back on the window, which is the bug."""
    assert controller(miaz).get_scope() == Gtk.ShortcutScope.LOCAL


def test_the_controller_is_on_the_column_view(miaz):
    assert controller(miaz).get_widget() is miaz.widget('workspace-view').cv


def test_the_controller_carries_every_list_scoped_binding(miaz):
    registry = miaz.service('shortcuts')
    wanted = {b.accelerator for b in registry.bindings(scope=sct.LIST)}
    assert wanted == {'Return', 'F2', 'Delete', '<Control>a', 'Escape'}
    installed = set()
    for shortcut in controller(miaz):
        installed.add(shortcut.get_trigger().to_string())
    for accelerator in wanted:
        ok, key, mods = Gtk.accelerator_parse(accelerator)
        assert Gtk.accelerator_name(key, mods) in installed or \
            accelerator in installed, f'{accelerator} is not installed'


def test_no_list_scoped_key_is_also_an_application_accelerator(miaz):
    """The regression test for the reason scoping exists. If Delete were also
    set on the application, it would fire while the search entry had focus."""
    registry = miaz.service('shortcuts')
    for binding in registry.bindings(scope=sct.LIST):
        assert miaz.app.get_accels_for_action(f'app.{binding.action}') == [], (
            f'{binding.action} is list scoped but also bound globally')


def test_the_hand_written_key_handler_is_gone(miaz):
    """Four keys used to be implemented by hand on a window controller. Two
    implementations of one key is the drift this work removes.

    The controller widget itself stays registered as 'window-event-controller':
    plugins such as MiAZFullscreen attach to it (F11), and removing it would
    silently break that extension point instead of the duplicate key handling
    this task actually removes. What must be gone is MiAZ's own handler.
    """
    mainwindow = miaz.widget('mainwindow')
    assert mainwindow is not None, 'the main window is not registered'
    assert not hasattr(mainwindow, '_on_key_pressed'), (
        'the hand written key handler is still defined on the main window')


def test_escape_is_not_a_global_accelerator(miaz):
    """A global accelerator is capture phase and runs before an
    Adw.AlertDialog, Adw.Dialog or Gtk.Popover gets to bubble-handle Escape
    itself, which would stop those dialogs and popovers from closing."""
    assert miaz.app.get_accels_for_action('app.filters-clear') == []


def test_escape_reaches_an_open_delete_confirmation_dialog(clean_view, monkeypatch):
    """This is the CRITICAL case the whole-branch review found: select
    documents, press Delete, an Adw.AlertDialog confirmation appears, press
    Escape to cancel. With Escape as a GLOBAL accelerator, GTK installs a
    CAPTURE phase Gtk.ShortcutController on the window that returns
    GDK_EVENT_STOP unconditionally. Capture runs before bubble, and the
    AlertDialog closes itself from a bubble phase handler on its own widget,
    so the window's controller ate the key first: the dialog stayed open and
    the workspace filters cleared behind it.

    Genuine key synthesis was tried first and could not be made to work in
    this harness: Gtk.test_widget_send_key and Gtk.test_widget_click are not
    introspectable through PyGObject on the installed GTK 4.22.5 (dir(Gtk)
    has neither name), GDK 4 provides no public constructor for a synthetic
    KeyEvent, and no xdotool, ydotool or wtype binary is installed to inject
    one at the compositor level. Injecting one that way would in any case
    land on whatever window has focus on the real, shared desktop session
    this harness runs on, not on this sandboxed test window, which is not
    safe to do from an automated test. So this test opens a real
    Adw.AlertDialog through the same document_delete() path the review
    describes, and asserts the invariant whose breakage was the actual bug:
    nothing at the window level claims Escape, while the document list's own
    LOCAL controller does, which is what lets a real Escape reach the
    dialog's own bubble phase handler instead of being stopped in capture.
    """
    srvdlg = clean_view.service('dialogs')
    captured = []
    real_show_confirmation = srvdlg.show_confirmation

    def spy(*args, **kwargs):
        dialog = real_show_confirmation(*args, **kwargs)
        captured.append(dialog)
        return dialog

    monkeypatch.setattr(srvdlg, 'show_confirmation', spy)
    try:
        clean_view.select_documents(DELETE_DOC)
        clean_view.service('actions').document_delete()
        clean_view.pump(0.3)
    finally:
        monkeypatch.undo()

    assert captured, 'the delete confirmation dialog was never created'
    dialog = captured[-1]
    try:
        assert isinstance(dialog, Adw.AlertDialog)
        assert dialog.get_root() is not None, (
            'the confirmation dialog did not open')

        # The bug: a GLOBAL accelerator is a capture phase controller on the
        # window, and capture runs before this open dialog's own bubble
        # phase Escape handling ever gets a look at the key.
        assert clean_view.app.get_accels_for_action('app.filters-clear') == [], (
            'filters-clear is still a global accelerator: it would capture '
            'Escape in the window before this open dialog ever saw it')

        # Escape still has a home: LOCAL scope on the document list, which is
        # where it belongs while the list has focus.
        held = controller(clean_view)
        assert held.get_scope() == Gtk.ShortcutScope.LOCAL
        ok, key, mods = Gtk.accelerator_parse('Escape')
        wanted = Gtk.accelerator_name(key, mods)
        installed = {shortcut.get_trigger().to_string() for shortcut in held}
        assert wanted in installed or 'Escape' in installed, (
            'Escape is not installed on the document list controller')
    finally:
        dialog.close()
        clean_view.pump(0.3)


def test_focus_can_land_in_the_document_list(miaz, clean_view):
    """LOCAL scope fires only while the list, or a widget inside it, has
    focus. If focus can never land there, F2 and Delete do nothing at all,
    which is worse than the behaviour they replace.

    Focus is walked upwards because a Gtk.ColumnView holds an inner list that
    is what actually takes focus.
    """
    cv = miaz.widget('workspace-view').cv
    cv.grab_focus()
    miaz.pump()
    focus = miaz.widget('window').get_focus()
    assert focus is not None, 'nothing in the window has focus'
    while focus is not None:
        if focus is cv:
            return
        focus = focus.get_parent()
    raise AssertionError('focus did not land inside the document list')
