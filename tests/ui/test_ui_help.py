#!/usr/bin/python3

"""UI: F1 and the Help menu item open the user help in its own window."""


def activate(driver, name):
    app = driver.app
    assert app.lookup_action(name) is not None, f"no action named '{name}'"
    app.activate_action(name, None)
    driver.pump()


def test_the_help_action_opens_the_help_window_on_the_first_steps(miaz):
    activate(miaz, 'app-help')
    window = miaz.widget('help-window')
    assert window is not None, 'app-help did not create the help window'
    assert window.get_visible()
    # Either the address asked for, or the page go.html already sent it to.
    uri = window.webview.get_uri() or ''
    assert 'id=first-steps' in uri or 'getting-started.html' in uri, uri
    window.close()
    miaz.pump()


def test_a_topic_loads_into_the_same_window(miaz):
    actions = miaz.service('actions')
    uri = actions.open_help('mass-rename')
    miaz.pump()
    first = miaz.widget('help-window')
    assert 'id=mass-rename' in uri
    actions.open_help('review')
    miaz.pump()
    assert miaz.widget('help-window') is first, 'a second topic built a second window'
    first.close()
    miaz.pump()


def test_closing_hides_the_window_and_the_next_topic_brings_it_back(miaz):
    actions = miaz.service('actions')
    actions.open_help('faq')
    miaz.pump()
    window = miaz.widget('help-window')
    window.close()
    miaz.pump()
    assert not window.get_visible()
    actions.open_help('shortcuts')
    miaz.pump()
    assert window.get_visible()
    window.close()
    miaz.pump()


def test_the_shortcuts_window_is_still_reachable(miaz):
    """F1 used to open the shortcuts list. That list keeps Ctrl+?."""
    from MiAZ.frontend.desktop.services import shortcuts as sct
    keys = {row[2]: row[3] for row in sct.CORE}
    assert keys['app-shortcuts'] == '<Control>question'
    assert keys['app-help'] == 'F1'
