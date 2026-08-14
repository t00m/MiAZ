#!/usr/bin/python3

"""UI: switching repositories. Checklist section 8.

This is the path the load() fix touched: the workspace, the vocabularies and
the index all have to follow the switch, and switching back must not show what
the other repository left behind.
"""

import json
import os

import pytest


def switch_to(driver, name):
    """Switch the way the settings dialog does: set current, then reload."""
    driver.app.get_config('App').set('current', name)
    workflow = driver.service('workflow')
    workflow.switch_start()
    driver.wait_until(lambda: driver.service('repo').docs.endswith(name),
                      message=f'the repository to become {name}')
    driver.wait_until(lambda: driver.workspace.is_loaded(),
                      message='the workspace to reload')
    driver.pump(0.5)


@pytest.fixture
def back_to_alpha(miaz):
    yield
    switch_to(miaz, 'Alpha')


def test_switching_reloads_the_documents(miaz, back_to_alpha):
    """8.1."""
    assert len(miaz.displayed()) == 3
    switch_to(miaz, 'Beta')
    assert len(miaz.displayed()) == 1
    assert miaz.displayed()[0].startswith('20250301')


def test_switching_reloads_the_vocabulary(miaz, sandbox, back_to_alpha):
    """8.2: the dropdowns must show the new repository's values."""
    beta_conf = os.path.join(sandbox['Beta'], '.conf')
    os.makedirs(beta_conf, exist_ok=True)
    with open(os.path.join(beta_conf, 'countries-used.json'), 'w',
              encoding='utf-8') as handler:
        json.dump({'PT': 'Portugal'}, handler)

    switch_to(miaz, 'Beta')
    countries = miaz.app.get_config('Country').load_used()
    assert set(countries) == {'PT'}


def test_switching_back_does_not_show_the_other_repository(miaz, sandbox,
                                                           back_to_alpha):
    """8.3: the stale cache bug, which two config tests also cover headless."""
    alpha_countries = set(miaz.app.get_config('Country').load_used())
    switch_to(miaz, 'Beta')
    switch_to(miaz, 'Alpha')
    assert set(miaz.app.get_config('Country').load_used()) == alpha_countries
    assert len(miaz.displayed()) == 3


def test_the_index_follows_the_switch(miaz, back_to_alpha):
    """8.1: the index is the view of one repository, not of the last two."""
    switch_to(miaz, 'Beta')
    index = miaz.service('index')
    assert len(index.documents()) == 1
    assert index.document('20250301-PT-EDU-SCHOOL-RPT-report-JOHNDOE.pdf')


# ---------------------------------------------------------------------------
# Switching in place, which is what replaced the restart
# ---------------------------------------------------------------------------

def loaded_plugins(driver):
    """The names of the plugins currently active."""
    manager = driver.service('plugin-system')
    return {plugin.get_name() for plugin in manager.plugins
            if manager.is_plugin_loaded(plugin)}


def switch_via_workflow(driver, name, set_default):
    """Switch the way the settings dialog does after the user confirms."""
    if set_default:
        driver.app.get_config('App').set('current', name)
    driver.service('workflow').switch_start(repo_id=name)
    driver.wait_until(lambda: driver.service('repo').docs.endswith(name),
                      message=f'the repository to become {name}')
    driver.wait_until(lambda: driver.workspace.is_loaded(),
                      message='the workspace to reload')
    driver.pump(0.5)


def test_the_plugins_follow_the_switch(miaz, back_to_alpha):
    """8.4: the gap the restart covered, the enabled set is per repository."""
    assert 'MiAZNotes' in loaded_plugins(miaz)

    switch_via_workflow(miaz, 'Beta', set_default=True)

    active = loaded_plugins(miaz)
    assert 'MiAZNotes' not in active, 'a plugin Beta does not enable stayed loaded'
    assert 'MiAZFullscreen' in active, 'a plugin Beta enables did not load'


def test_switching_back_restores_the_plugins(miaz, back_to_alpha):
    switch_via_workflow(miaz, 'Beta', set_default=True)
    switch_via_workflow(miaz, 'Alpha', set_default=True)
    assert 'MiAZNotes' in loaded_plugins(miaz)


def test_switching_without_setting_the_default(miaz, back_to_alpha):
    """The checkbox unticked: look at Beta, still open Alpha next time."""
    switch_via_workflow(miaz, 'Beta', set_default=False)

    assert miaz.service('repo').docs.endswith('Beta')
    assert len(miaz.displayed()) == 1
    assert miaz.app.get_config('App').get('current') == 'Alpha'


def test_the_active_repository_is_the_one_on_screen(miaz, back_to_alpha):
    """What the window title and the sidebar name after a non-default switch."""
    switch_via_workflow(miaz, 'Beta', set_default=False)
    assert miaz.service('repo').get_active_id() == 'Beta'


def test_an_unknown_repository_changes_nothing(miaz):
    """An id that is not in use must leave the repository on screen alone."""
    before = miaz.service('repo').docs
    assert miaz.service('workflow').switch_start(repo_id='Nope') is False
    assert miaz.service('repo').docs == before
    assert 'MiAZNotes' in loaded_plugins(miaz)
