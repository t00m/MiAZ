#!/usr/bin/python3

"""UI: startup must not repeat work once per plugin.

Both checks here come from reading a real startup log, where the plugin
directories were scanned twice and the browser page was told to load the same
URL seventeen times, once per plugin activated.
"""

import os

import pytest


def test_a_repository_switch_does_not_rescan_the_plugin_directories(clean_view):
    """What is on disk does not depend on which repository is open.

    The scan parses every plugin module with ast, so running it per switch is
    pure waste, and it used to run once more at startup with its result thrown
    away because no repository was open yet to write it to.
    """
    pluginsystem = clean_view.service('plugin-system')
    scans = []
    real_scan = pluginsystem.scan_plugin_index

    def counting_scan(*args, **kwargs):
        scans.append(1)
        return real_scan(*args, **kwargs)

    pluginsystem.scan_plugin_index = counting_scan
    try:
        repository = clean_view.service('repo')
        repository.emit('repository-switched')
        clean_view.pump(0.5)
        assert scans == [], f'{len(scans)} rescan(s) on a repository switch'
    finally:
        pluginsystem.scan_plugin_index = real_scan


def test_a_repository_switch_still_writes_the_available_plugins(clean_view):
    """Dropping the rescan must not drop the per-repository update with it."""
    pluginsystem = clean_view.service('plugin-system')
    updates = []
    real_update = pluginsystem.update_available_plugins

    def counting_update(*args, **kwargs):
        updates.append(1)
        return real_update(*args, **kwargs)

    pluginsystem.update_available_plugins = counting_update
    try:
        clean_view.service('repo').emit('repository-switched')
        clean_view.pump(0.5)
        assert updates, 'the available plugin set was not written on a switch'
    finally:
        pluginsystem.update_available_plugins = real_update


def test_the_available_plugin_set_matches_what_is_on_disk(clean_view):
    """The end result of the split has to be what it was before it."""
    pluginsystem = clean_view.service('plugin-system')
    scanned = {name for name, _desc in pluginsystem.scan_plugin_index()}
    pluginsystem.update_available_plugins()
    clean_view.pump(0.3)
    available = set(clean_view.app.get_config('Plugin').load_available().keys())
    assert scanned == available


@pytest.fixture
def browser_with_a_page(clean_view):
    """The browser page, with one WWW page on disk to load.

    The sandbox enables no plugin that publishes a page, and with no pages
    _refresh_pages returns before it would ever load one, so both tests below
    would pass without testing anything.
    """
    page = clean_view.widget('workspace-browser')
    if page is None:
        pytest.skip('the browser page is not built in this configuration')
    root = page._www_root()
    page_dir = os.path.join(root, 'TestPage')
    os.makedirs(page_dir, exist_ok=True)
    with open(os.path.join(page_dir, 'index.html'), 'w', encoding='utf-8') as handler:
        handler.write('<html><body>test</body></html>')
    page._refresh_pages()
    clean_view.pump(0.6)
    assert page.has_pages(), 'the seeded page was not picked up'
    yield page


def test_loading_many_plugins_reloads_the_browser_page_once(clean_view, browser_with_a_page):
    """The browser page listens to 'plugins-updated', which the loader emits
    once per plugin. Eighteen plugins meant eighteen scans of one directory and
    eighteen load_uri calls for the same URL."""
    page = browser_with_a_page
    loads = []
    real_load = page._load_page
    page._load_page = lambda index: loads.append(index) or real_load(index)
    try:
        plugin_system = clean_view.service('plugin-system')
        for _round in range(8):
            plugin_system.emit('plugins-updated')
        clean_view.pump(0.8)
        assert len(loads) <= 1, f'{len(loads)} page loads for one burst'
    finally:
        page._load_page = real_load


def test_an_unchanged_refresh_does_not_reload_the_page(clean_view, browser_with_a_page):
    """Reloading throws away scroll position and any state the page holds."""
    page = browser_with_a_page
    loads = []
    real_load = page._load_page
    page._load_page = lambda index: loads.append(index) or real_load(index)
    try:
        page._refresh_pages()
        clean_view.pump(0.3)
        assert loads == [], 'an unchanged page set still reloaded the view'
        # Content on disk changing is the case that must still reload.
        page._refresh_pages(force_reload=True)
        clean_view.pump(0.3)
        assert len(loads) == 1, 'a forced refresh did not reload the view'
    finally:
        page._load_page = real_load
