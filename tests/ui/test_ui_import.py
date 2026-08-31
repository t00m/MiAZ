#!/usr/bin/python3

"""UI: the import and clipboard actions that used to be plugins.

MiAZAddFromDir and MiAZCopy2Clipboard are core now, so neither needs a plugin
enabled to work. That is what these tests hold down: the entries exist in the
menus the moment the window is built, and the actions do what the plugins did.
"""

import os


def _write(path, text='document'):
    with open(path, 'w', encoding='utf-8') as handler:
        handler.write(text)
    return path


def _imported(driver, marker):
    docs = driver.service('repo').docs
    return [name for name in os.listdir(docs) if marker in name.lower()]


def _cleanup(driver, marker):
    docs = driver.service('repo').docs
    for name in _imported(driver, marker):
        os.unlink(os.path.join(docs, name))
    driver.pump(0.4)


def _select_one(driver, document, attempts=5):
    """Select one document, and keep at it until the selection holds.

    An import in an earlier test leaves a refresh in flight, and a refresh
    rebuilds the model and drops the selection made a moment before it.
    """
    for _ in range(attempts):
        driver.wait_until(lambda: document in driver.displayed(),
                          message='the document to be listed')
        driver.select_documents(document)
        driver.pump(0.4)
        selected = [item.id for item in driver.workspace.get_selected_items()]
        if selected == [document]:
            return True
    return False


def _labels(menu):
    """Every label in a Gio.Menu, its sections and submenus included."""
    found = []
    for position in range(menu.get_n_items()):
        label = menu.get_item_attribute_value(position, 'label', None)
        if label is not None:
            found.append(label.get_string())
        for link in ('section', 'submenu'):
            child = menu.get_item_link(position, link)
            if child is not None:
                found.extend(_labels(child))
    return found


def test_the_add_menu_holds_both_core_entries(miaz):
    """One for files, one for a directory, neither from a plugin."""
    add_menu = miaz.widget('headerbar-add-menu')
    labels = _labels(add_menu)
    assert 'Add new document(s)' in labels
    assert 'Add documents from a directory' in labels


def test_the_selection_menu_holds_copy_document_names(miaz):
    menu = miaz.widget('workspace-menu-selection')
    assert 'Copy document names' in _labels(menu)


def test_the_import_service_offers_a_directory_action(miaz):
    importdoc = miaz.service('importdoc')
    assert importdoc.menuitem_dir is not None
    assert hasattr(importdoc, 'import_directory')


def test_importing_a_directory_asks_about_subfolders(miaz, tmp_path):
    """The chosen folder goes through the same question a dropped one does."""
    root = str(tmp_path)
    os.makedirs(os.path.join(root, 'folder', 'sub'))
    _write(os.path.join(root, 'folder', 'dirone.pdf'))
    _write(os.path.join(root, 'folder', 'sub', 'dirtwo.pdf'))

    importdoc = miaz.service('importdoc')
    dialog = importdoc.import_dropped([os.path.join(root, 'folder')])
    miaz.pump(0.3)
    try:
        assert dialog is not None
        assert '1' in miaz.widget('import-drop-count').get_text()
        miaz.widget('import-drop-recursive').set_active(True)
        miaz.pump(0.2)
        assert '2' in miaz.widget('import-drop-count').get_text()
        dialog.emit('response', 'apply')
        miaz.pump(0.6)
        assert len(_imported(miaz, 'dirone')) == 1
        assert len(_imported(miaz, 'dirtwo')) == 1
    finally:
        _cleanup(miaz, 'dir')


def test_copying_names_copies_the_selection(miaz):
    """The action returns what it put on the clipboard.

    The clipboard is not read back: on Wayland only a focused client may set
    it, so the value in a headless run says more about the compositor than
    about MiAZ. What is copied is composed by document_names_text, covered in
    tests/test_actions.py.
    """
    document = '20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf'
    assert _select_one(miaz, document), 'the document could not be selected'

    actions = miaz.service('actions')
    assert actions.document_copy_names() == document

    miaz.workspace.unselect_items()
    miaz.pump(0.2)


def test_copying_nothing_does_nothing(miaz):
    """With no selection the action stops instead of clearing the clipboard."""
    miaz.workspace.unselect_items()
    miaz.pump(0.2)
    actions = miaz.service('actions')
    assert actions.document_copy_names() is None


def test_a_big_import_is_handed_to_a_worker(miaz, tmp_path):
    """Over the threshold the copy leaves the main loop, and still lands."""
    root = str(tmp_path)
    os.makedirs(os.path.join(root, 'many'))
    count = 25
    for number in range(count):
        _write(os.path.join(root, 'many', f'bulk{number:02d}.pdf'))

    importdoc = miaz.service('importdoc')
    paths = [os.path.join(root, 'many', name)
             for name in sorted(os.listdir(os.path.join(root, 'many')))]
    try:
        # The batched path reports from the main loop later, so it returns None.
        assert importdoc.import_paths(paths) is None
        miaz.wait_until(lambda: len(_imported(miaz, 'bulk')) == count,
                        message='the background import to finish')
    finally:
        _cleanup(miaz, 'bulk')
