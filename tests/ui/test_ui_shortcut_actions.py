#!/usr/bin/python3

"""UI: the actions the new keyboard shortcuts activate.

The keys themselves are tested in tests/ui/test_ui_shortcuts.py. This file
tests that each action does the thing its label promises, by activating it the
way GTK does when the key is pressed.
"""

import pytest

# tests/ui is not a package, so pytest puts this directory on sys.path
# and the shared helpers in conftest.py import by their bare module
# name. Only fixtures arrive on their own; a plain function does not.
from conftest import skip_unless_focus_observable


def activate(driver, name):
    """Activate an application action the way an accelerator would."""
    app = driver.app
    assert app.lookup_action(name) is not None, f"no action named '{name}'"
    app.activate_action(name, None)
    driver.pump()


def focus_is_inside(driver, widget_name):
    """Whether the window's focus widget is the named widget, or is nested
    inside it.

    has_focus() is no good here: it additionally requires the toplevel window
    to be window-manager-active, which a process spawned outside a real
    desktop session never becomes. What grab_focus() actually does, and what
    is observable regardless of window activation, is move
    window.get_focus(). A Gtk.SearchEntry does not receive that focus itself:
    it delegates to an internal Gtk.Text, so the check has to walk up the
    parent chain rather than compare identity directly.
    """
    target = driver.widget(widget_name)
    focus = driver.widget('window').get_focus()
    while focus is not None:
        if focus is target:
            return True
        focus = focus.get_parent()
    return False


def test_every_shortcut_action_exists(miaz):
    """A key bound to an action that does not exist does nothing at all, and
    does it silently. The table and the actions must agree."""
    from MiAZ.frontend.desktop.services import shortcuts as sct
    missing = [row[2] for row in sct.CORE
               if miaz.app.lookup_action(row[2]) is None]
    assert missing == [], f"the table binds actions that do not exist: {missing}"


@pytest.mark.parametrize('name,view', [
    ('view-details', 'details'),
    ('view-grid', 'grid'),
    ('view-timeline', 'timeline'),
    ('view-conversation', 'conversation'),
    ('view-filenames', 'filenames'),
])
def test_the_view_actions_switch_the_view(miaz, clean_view, name, view):
    activate(miaz, name)
    assert miaz.workspace._view_stack.get_visible_child_name() == view


def test_the_sidebar_action_toggles_the_sidebar(miaz):
    split = miaz.widget('main-split-view')
    before = split.get_show_sidebar()
    activate(miaz, 'sidebar-toggle')
    assert split.get_show_sidebar() is not before
    activate(miaz, 'sidebar-toggle')
    assert split.get_show_sidebar() is before


def test_the_preview_action_toggles_the_preview_sheet(miaz):
    sheet = miaz.widget('workspace-preview-sheet')
    before = sheet.get_open()
    activate(miaz, 'preview-toggle')
    assert sheet.get_open() is not before
    activate(miaz, 'preview-toggle')
    assert sheet.get_open() is before


def test_the_search_action_puts_the_cursor_in_the_search_entry(
        miaz, focus_observable):
    """Hide the sidebar first, rather than trust it is already open. On a
    fresh install the sidebar starts hidden, and grab_focus needs a mapped
    widget, so this proves the action reveals it rather than depending on an
    earlier test, such as test_the_sidebar_action_toggles_the_sidebar above,
    having left it open.

    The sidebar half runs everywhere. The focus half needs a display that
    reflects grab_focus(), which is what focus_observable answers.
    """
    split = miaz.widget('main-split-view')
    split.set_show_sidebar(False)
    miaz.pump()
    activate(miaz, 'search-focus')
    assert split.get_show_sidebar(), 'search-focus did not reveal the sidebar'
    skip_unless_focus_observable(focus_observable)
    assert focus_is_inside(miaz, 'searchentry')


def test_the_concept_search_action_focuses_the_concept_entry(
        miaz, focus_observable):
    """See test_the_search_action_puts_the_cursor_in_the_search_entry: the
    sidebar is hidden first so this does not depend on test order either."""
    split = miaz.widget('main-split-view')
    split.set_show_sidebar(False)
    miaz.pump()
    activate(miaz, 'search-focus-concept')
    assert split.get_show_sidebar(), (
        'search-focus-concept did not reveal the sidebar')
    skip_unless_focus_observable(focus_observable)
    assert focus_is_inside(miaz, 'searchentry-concept')


def test_clearing_filters_empties_the_search_entry(miaz, clean_view):
    entry = miaz.widget('searchentry')
    entry.set_text('something')
    miaz.pump()
    activate(miaz, 'filters-clear')
    assert entry.get_text() == ''


def test_select_all_selects_every_visible_document(miaz, clean_view):
    activate(miaz, 'document-select-all')
    view = miaz.widget('workspace-view')
    model = view.cv.get_model()
    assert model.get_selection().get_size() == model.get_n_items()
    assert model.get_n_items() > 0


def test_an_action_does_not_raise_before_its_widget_exists():
    """The actions are created while the services are still being built. A key
    pressed then must not take the application down."""
    from MiAZ.frontend.desktop.services.actions import MiAZActions

    class Bare:
        """Answers None to everything. It is its own .app because the
        handlers reach widgets through self.app.get_widget."""

        def __init__(self):
            self.app = self

        def get_service(self, name):
            return None

        def get_widget(self, name):
            return None

    bare = Bare()
    MiAZActions.shortcut_show_view(bare, 'grid')
    MiAZActions.shortcut_toggle_sidebar(bare)
    MiAZActions.shortcut_focus_search(bare, 'searchentry')
    MiAZActions.shortcut_clear_filters(bare)
    MiAZActions.shortcut_select_all(bare)
    MiAZActions.shortcut_popup(bare, 'headerbar-button-massrename')


def test_stop_if_no_items_tolerates_no_workspace():
    """repo-management, repo-settings, document-open, document-rename and
    document-delete all route through here before doing anything else. No
    workspace means no selection, which is what True already means to every
    caller: do not proceed. This runs before the main window exists, so there
    is also no toast overlay to show one in."""
    from MiAZ.frontend.desktop.services.actions import MiAZActions

    class Bare:
        """Answers None to everything, same shape as the guard test above."""

        def __init__(self):
            self.app = self

        def get_widget(self, name):
            return None

    bare = Bare()
    assert MiAZActions.stop_if_no_items(bare) is True
