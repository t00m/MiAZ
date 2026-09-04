#!/usr/bin/python3

"""UI: the Repository Settings dialog.

Per-repository settings used to be split across three places: an inline group
in the Application Settings dialog, a per-plugin dialog behind a button in the
Plugins tab, and nothing at all for the rest. These check they arrive in one.
"""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Adw

import pytest


@pytest.fixture
def repo_settings(clean_view):
    """The dialog, opened, with its widgets registered."""
    clean_view.service('actions').show_repository_settings()
    clean_view.pump(0.5)
    window = clean_view.widget('window-repo-settings')
    assert window is not None, 'the repository settings window did not open'
    yield window
    window.close()
    clean_view.pump(0.3)


def row_titles(widget):
    """The title of every Adw.PreferencesRow anywhere under `widget`.

    A group wraps its rows in boxes and list boxes, and an ExpanderRow holds
    more rows inside itself, so this walks the whole tree rather than the
    direct children.
    """
    found = []
    if isinstance(widget, Adw.PreferencesRow):
        found.append(widget.get_title())
    child = widget.get_first_child()
    while child is not None:
        found.extend(row_titles(child))
        child = child.get_next_sibling()
    return found


def test_the_settings_tab_is_there(repo_settings, clean_view):
    page = clean_view.widget('repository-settings-page-settings')
    assert page is not None, 'no Settings tab'


def test_the_settings_tab_names_the_repository(repo_settings, clean_view):
    page = clean_view.widget('repository-settings-page-settings')
    row_name = clean_view.widget('repository-settings-row-name')
    row_path = clean_view.widget('repository-settings-row-location')
    assert row_name is not None and row_path is not None
    repo = clean_view.service('repo')
    assert row_path.get_subtitle() == repo.docs


def test_nothing_is_built_until_the_tab_is_shown(repo_settings, clean_view):
    """The guard that keeps the scanner asleep. AutoScan builds its group by
    running SANE, so opening this dialog must not call any builder."""
    page = clean_view.widget('repository-settings-page-settings')
    assert page.is_built() is False
    notebook = clean_view.widget('repository-settings-notebook')
    notebook.set_current_page(_page_number(notebook, page))
    clean_view.pump(0.4)
    assert page.is_built() is True


def _page_number(notebook, page):
    for number in range(notebook.get_n_pages()):
        child = notebook.get_nth_page(number)
        if child is page or (hasattr(child, 'get_first_child')
                             and child.get_first_child() is page):
            return number
    raise AssertionError('page is not in the notebook')
