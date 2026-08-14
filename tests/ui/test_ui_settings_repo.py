#!/usr/bin/python3

"""UI: switching repositories from Settings. Checklist section 8.

The repository dropdown in Settings used to restart the application. It now
switches in place, and a checkbox decides whether the repository also becomes
the default. What is driven here is the response handler, the branch the user
reaches by confirming the dialog: presenting an Adw.AlertDialog and clicking
its button needs a real pointer, but everything the button does lives here.
"""

import json
import os

import pytest

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk


@pytest.fixture
def settings(miaz):
    """The application settings dialog, built and reachable."""
    miaz.service('actions').show_app_settings()
    miaz.pump(0.3)
    dialog = miaz.widget('window-settings')
    assert dialog is not None, 'the settings dialog was not registered'
    yield dialog
    dialog.close()
    miaz.pump(0.2)


@pytest.fixture
def back_to_alpha(miaz):
    yield
    miaz.app.get_config('App').set('current', 'Alpha')
    miaz.service('workflow').switch_start(repo_id='Alpha')
    miaz.wait_until(lambda: miaz.service('repo').docs.endswith('Alpha'),
                    message='the repository to become Alpha')
    miaz.pump(0.3)


def repo_item(miaz, name):
    """The dropdown entry for a repository, which is what the handler receives."""
    dropdown = miaz.widget('window-settings-dropdown-repository-active')
    for position in range(len(dropdown.get_model())):
        item = dropdown.get_model().get_item(position)
        if item.id == name:
            return item
    raise AssertionError(f'{name} is not in the repository dropdown')


def confirm(miaz, settings, name, set_default):
    """Answer the confirmation dialog the way the user would."""
    check = Gtk.CheckButton()
    check.set_active(set_default)
    settings._on_use_repo_response(None, 'apply', (repo_item(miaz, name), check))
    miaz.wait_until(lambda: miaz.service('repo').docs.endswith(name),
                    message=f'the repository to become {name}')
    miaz.wait_until(lambda: miaz.workspace.is_loaded(),
                    message='the workspace to reload')
    miaz.pump(0.5)


def test_confirming_switches_and_sets_the_default(miaz, settings, back_to_alpha):
    """8.5: the checkbox ticked, which is what the restart used to do."""
    confirm(miaz, settings, 'Beta', set_default=True)

    assert miaz.service('repo').docs.endswith('Beta')
    assert miaz.app.get_config('App').get('current') == 'Beta'
    assert miaz.service('repo').get_active_id() == 'Beta'


def test_confirming_without_the_checkbox_keeps_the_default(miaz, settings,
                                                           back_to_alpha):
    """8.6: look at another repository, keep opening this one."""
    confirm(miaz, settings, 'Beta', set_default=False)

    assert miaz.service('repo').docs.endswith('Beta')
    assert miaz.app.get_config('App').get('current') == 'Alpha'
    assert miaz.service('repo').get_active_id() == 'Beta'


def test_the_default_written_survives_a_restart(miaz, settings, sandbox,
                                                back_to_alpha):
    """The checkbox writes what the next start reads, not just what is shown."""
    confirm(miaz, settings, 'Beta', set_default=True)

    conf = os.path.join(sandbox['home'], '.MiAZ', 'etc', 'MiAZ-application.json')
    with open(conf, encoding='utf-8') as handler:
        assert json.load(handler)['current'] == 'Beta'


def test_cancelling_leaves_the_repository_alone(miaz, settings):
    """8.7: declining puts the dropdown back and switches nothing."""
    before = miaz.service('repo').docs
    check = Gtk.CheckButton()

    settings._on_use_repo_response(None, 'cancel', (repo_item(miaz, 'Beta'), check))
    miaz.pump(0.3)

    assert miaz.service('repo').docs == before
    assert miaz.app.get_config('App').get('current') == 'Alpha'
    dropdown = miaz.widget('window-settings-dropdown-repository-active')
    assert dropdown.get_selected_item().id == 'Alpha'


def test_the_window_title_names_the_repository_on_screen(miaz, settings,
                                                         back_to_alpha):
    """A non-default switch must not leave the window naming the default one."""
    confirm(miaz, settings, 'Beta', set_default=False)

    sidebar_label = miaz.widget('sidebar-title-label')
    assert 'Beta' in sidebar_label.get_text()
