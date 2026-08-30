#!/usr/bin/python3

"""UI: the shape of the plugin section of the workspace menu.

The other plugin tests count what a plugin contributes and check it is given
back on unload. None of them looked at where the entries end up, and the
answer was: too deep, and in more places than there are ideas.

MiAZNotes hung Backup and Restore off two top-level entries of their own,
holding one item each, while its own entry sat elsewhere. MiAZProjectMgt and
MiAZPeriodicity each put a submenu named after the plugin inside the entry
already named after the plugin, so reaching Assign meant Projects, then
Project, then Assign.
"""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gio

import pytest


def labels(menu):
    """The label of every item directly in `menu`, sections flattened."""
    found = []
    if menu is None:
        return found
    for position in range(menu.get_n_items()):
        value = menu.get_item_attribute_value(position, 'label', None)
        if value is not None:
            found.append(value.get_string())
        section = menu.get_item_link(position, Gio.MENU_LINK_SECTION)
        if section is not None:
            found.extend(labels(section))
    return found


def submenus(menu):
    """{label: Gio.Menu} for every submenu directly in `menu`."""
    found = {}
    if menu is None:
        return found
    for position in range(menu.get_n_items()):
        child = menu.get_item_link(position, Gio.MENU_LINK_SUBMENU)
        if child is None:
            continue
        value = menu.get_item_attribute_value(position, 'label', None)
        found[value.get_string() if value is not None else ''] = child
    return found


@pytest.fixture
def plugin_menus(miaz):
    section = miaz.widget('workspace-plugins-section')
    assert section is not None, 'the workspace menu has no plugins section'
    return submenus(section)


def entry(plugin_menus, label, plugin_name):
    if label not in plugin_menus:
        pytest.skip(f'{plugin_name} is not enabled in this repository')
    return plugin_menus[label]


def test_notes_holds_all_four_of_its_actions(plugin_menus):
    notes = entry(plugin_menus, 'Notes', 'MiAZNotes')
    found = labels(notes)
    assert 'Create a new note' in found
    assert 'See all notes…' in found
    assert 'Backup notes' in found
    assert 'Restore notes' in found


def test_backup_and_restore_are_not_entries_of_their_own(plugin_menus):
    """They act on the notes, so they belong with the notes."""
    assert 'Backup' not in plugin_menus
    assert 'Restore' not in plugin_menus


def test_projects_holds_its_actions_directly(plugin_menus):
    projects = entry(plugin_menus, 'Projects', 'MiAZProjectMgt')
    assert submenus(projects) == {}, 'Projects still nests a submenu'
    found = labels(projects)
    assert any(text.startswith('Assign document(s)') for text in found), found
    assert any(text.startswith('Unassign document(s)') for text in found), found
    assert any(text.startswith('Manage') for text in found), found


def test_tags_holds_its_actions_directly(plugin_menus):
    tags = entry(plugin_menus, 'Tags', 'MiAZPeriodicity')
    assert submenus(tags) == {}, 'Tags still nests a submenu'
    found = labels(tags)
    assert any(text.startswith('Set ') for text in found), found
    assert any(text.startswith('Unset ') for text in found), found
    assert any(text.startswith('Manage ') for text in found), found


def test_no_plugin_entry_nests_a_submenu_of_its_own_name(plugin_menus):
    """A submenu repeating its parent's name is a level that says nothing."""
    for label, menu in plugin_menus.items():
        for inner in submenus(menu):
            assert inner.lower().rstrip('s') != label.lower().rstrip('s'), \
                f'{label} nests a submenu named {inner}'


def test_one_note_is_filed_against_every_selected_document(miaz):
    """The Ctrl+N entry used to do nothing unless exactly one row was picked."""
    plugin_obj = miaz.widget('plugin-MiAZNotes')
    if plugin_obj is None:
        pytest.skip('MiAZNotes is not enabled in this repository')

    document_ids = miaz.displayed()[:3]
    assert len(document_ids) >= 2, 'need two documents to file one note against'

    store = plugin_obj.store
    before = {doc_id: store.count_for_document(doc_id) for doc_id in document_ids}

    miaz.select_documents(*document_ids)
    plugin_obj._on_new_doc_note()
    miaz.pump(0.4)

    window = plugin_obj._win_per_doc
    assert window is not None, 'the notes window did not open'
    assert window.document_ids == document_ids

    created = []
    try:
        window.editor.load(window.editor.header(), 'one note, several files',
                           editable=True)
        window._on_save_requested(None)
        miaz.pump(0.3)

        for doc_id in document_ids:
            after = store.count_for_document(doc_id)
            assert after == before[doc_id] + 1, f'{doc_id} got {after - before[doc_id]} notes'
            created.extend(store.list_for_document(doc_id))
    finally:
        # The application is built once for the whole session, so the notes
        # written here would otherwise follow every test that runs after.
        for note_path in created:
            header, body = store.read(note_path)
            if body.strip() == 'one note, several files':
                store.delete(note_path)
        window.destroy()
        plugin_obj._win_per_doc = None
        miaz.pump(0.2)
