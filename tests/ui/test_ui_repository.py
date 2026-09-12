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


def test_switching_reloads_the_documents(clean_view, back_to_alpha):
    """8.1.

    clean_view, not miaz, because these counts are about what the repository
    holds. The workspace opens on the nearest date preset that is not empty
    (pick_date_preset), and the sandbox documents carry fixed dates, so which
    preset that is depends on the day the suite runs: on 9 September 2026 the
    walk stopped at "since last 3 months", which holds one of Alpha's three.
    Selecting "all documents" first is what the other files already do.
    """
    assert len(clean_view.displayed()) == 3
    switch_to(clean_view, 'Beta')
    assert len(clean_view.displayed()) == 1
    assert clean_view.displayed()[0].startswith('20250301')


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


def test_switching_back_does_not_show_the_other_repository(clean_view, sandbox,
                                                           back_to_alpha):
    """8.3: the stale cache bug, which two config tests also cover headless."""
    alpha_countries = set(clean_view.app.get_config('Country').load_used())
    switch_to(clean_view, 'Beta')
    switch_to(clean_view, 'Alpha')
    assert set(clean_view.app.get_config('Country').load_used()) == alpha_countries
    assert len(clean_view.displayed()) == 3


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
    assert 'MiAZPeriodicity' in loaded_plugins(miaz)

    switch_via_workflow(miaz, 'Beta', set_default=True)

    active = loaded_plugins(miaz)
    assert 'MiAZPeriodicity' not in active, 'a plugin Beta does not enable stayed loaded'
    assert 'MiAZFullscreen' in active, 'a plugin Beta enables did not load'


def test_switching_back_restores_the_plugins(miaz, back_to_alpha):
    switch_via_workflow(miaz, 'Beta', set_default=True)
    switch_via_workflow(miaz, 'Alpha', set_default=True)
    assert 'MiAZPeriodicity' in loaded_plugins(miaz)


def test_switching_without_setting_the_default(clean_view, back_to_alpha):
    """The checkbox unticked: look at Beta, still open Alpha next time."""
    switch_via_workflow(clean_view, 'Beta', set_default=False)

    assert clean_view.service('repo').docs.endswith('Beta')
    assert len(clean_view.displayed()) == 1
    assert clean_view.app.get_config('App').get('current') == 'Alpha'


def test_the_active_repository_is_the_one_on_screen(miaz, back_to_alpha):
    """What the window title and the sidebar name after a non-default switch."""
    switch_via_workflow(miaz, 'Beta', set_default=False)
    assert miaz.service('repo').get_active_id() == 'Beta'


def _menu_labels(menu):
    """Every label in a Gio.Menu, its sections and submenus included."""
    found = []
    for position in range(menu.get_n_items()):
        label = menu.get_item_attribute_value(position, 'label', None)
        if label is not None:
            found.append(label.get_string())
        for link in ('section', 'submenu'):
            child = menu.get_item_link(position, link)
            if child is not None:
                found.extend(_menu_labels(child))
    return found


@pytest.fixture
def empty_repository(miaz, sandbox, back_to_alpha):
    """A new repository with nothing in it, open on screen."""
    path = os.path.join(sandbox['home'], 'Empty')
    os.makedirs(path, exist_ok=True)
    miaz.app.get_config('Repository').set_repo_used('Empty', path, 'Empty')
    miaz.pump(0.3)
    switch_via_workflow(miaz, 'Empty', set_default=False)
    yield path


def test_an_empty_repository_offers_to_add_documents(miaz, empty_repository):
    """A new repository opens on the empty page, with an Add button.

    It opened on a "No documents found" page with no buttons, and the toolbar
    that holds Add was hidden behind it, so the first document could not be
    added at all.
    """
    assert miaz.displayed() == []
    assert miaz.widget('stack').get_visible_child_name() == 'workspace'
    assert not miaz.widget('workspace-toolbar').get_mapped()
    empty = miaz.widget('workspace-empty')
    assert empty.get_mapped()
    assert empty.button_add.get_mapped()
    assert empty.button_add.get_menu_model() is miaz.widget('headerbar-add-menu')
    labels = _menu_labels(empty.button_add.get_menu_model())
    assert 'Add new document(s)' in labels
    assert 'Add documents from a directory' in labels
    # Nothing is waiting for review in a repository with no documents.
    assert not empty.button_review.get_mapped()


def test_the_empty_page_lists_enabled_import_plugins(miaz, empty_repository):
    """An Import plugin enabled for the repository adds its entry to the menu."""
    system = miaz.service('plugin-system')
    info = next(i for i in system.plugins if i.get_name() == 'MiAZImportFromZip')
    empty = miaz.widget('workspace-empty')
    assert 'Import documents from ZIP' not in _menu_labels(empty.button_add.get_menu_model())

    system.load_plugin(info)
    try:
        miaz.wait_until(
            lambda: 'Import documents from ZIP' in _menu_labels(
                empty.button_add.get_menu_model()),
            message='the ZIP entry in the Add menu')
    finally:
        system.unload_plugin(info)
        miaz.pump(0.5)
    assert 'Import documents from ZIP' not in _menu_labels(empty.button_add.get_menu_model())


def test_the_empty_page_leads_to_documents_waiting_for_review(miaz, empty_repository):
    """The first document usually lands in Review, so the view stays empty.

    Review lives on the toolbar, which the empty page hides, so the page
    offers it too. Pressing it shows the document and brings the toolbar back.
    """
    empty = miaz.widget('workspace-empty')
    toggle = miaz.widget('workspace-togglebutton-pending-docs')
    normalized = '-----BANK_STATEMENT-.pdf'
    with open(os.path.join(empty_repository, 'bank statement.pdf'), 'w',
              encoding='utf-8') as handler:
        handler.write('scanned')
    try:
        miaz.wait_until(lambda: empty.button_review.get_mapped(),
                        message='the Review button on the empty page')
        assert miaz.displayed() == []

        empty.button_review.emit('clicked')
        miaz.wait_until(lambda: normalized in miaz.displayed(),
                        message='the document to show in Review')
        miaz.pump(0.3)
        assert toggle.get_active()
        assert miaz.widget('workspace-toolbar').get_mapped()
        assert not empty.get_mapped()
    finally:
        toggle.set_active(False)
        for name in ('bank statement.pdf', normalized):
            path = os.path.join(empty_repository, name)
            if os.path.exists(path):
                os.unlink(path)
        miaz.pump(0.5)


def test_an_unknown_repository_changes_nothing(miaz):
    """An id that is not in use must leave the repository on screen alone."""
    before = miaz.service('repo').docs
    assert miaz.service('workflow').switch_start(repo_id='Nope') is False
    assert miaz.service('repo').docs == before
    assert 'MiAZPeriodicity' in loaded_plugins(miaz)


def test_a_repository_whose_directory_is_gone(miaz, sandbox, back_to_alpha):
    """8.10: renaming a repository directory away must not recreate it.

    setup() used to init() whatever path was configured, and os.makedirs
    creates the whole path, so MiAZ opened an empty repository with empty
    configuration exactly where the documents used to be.
    """
    missing = os.path.join(sandbox['home'], 'Ghost')
    repos = miaz.app.get_config('Repository')
    repos.set_repo_used('Ghost', missing, 'Ghost')
    miaz.pump(0.3)

    assert miaz.service('workflow').switch_start(repo_id='Ghost') is False
    miaz.pump(0.5)

    assert not os.path.exists(missing), 'the missing directory was recreated'
    assert 'not found' in str(miaz.service('repo').get_error())
