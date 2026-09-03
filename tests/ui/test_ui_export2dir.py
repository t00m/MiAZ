#!/usr/bin/python3

"""UI: exporting documents to a directory, in the running application.

The pure part of the plugin is covered by tests/test_export2dir.py. What only
the real application can answer is here: the plugin loads, the dialog refuses
to start without a folder, the copy happens off the main loop behind the
progress dialog, and what the last export used comes back the next time.
"""

import os

import pytest

PLUGIN = 'MiAZExport2Dir'


def find_plugin(system, name):
    for info in system.plugins:
        if info.get_name() == name:
            return info
    return None


@pytest.fixture
def export2dir(miaz):
    """The loaded plugin object, with two documents selected."""
    system = miaz.service('plugin-system')
    info = find_plugin(system, PLUGIN)
    if info is None:
        pytest.skip(f'{PLUGIN} is not available in this repository')
    if not info.is_loaded():
        system.load_plugin(info)
        miaz.pump(0.5)
    plugin_obj = miaz.widget(f'plugin-{PLUGIN}')
    assert plugin_obj is not None, f'{PLUGIN} did not register itself'

    document_ids = miaz.displayed()[:2]
    assert len(document_ids) >= 1, 'no documents to export'
    miaz.select_documents(*document_ids)
    miaz.pump(0.3)
    return plugin_obj


def dialogs_closed(miaz):
    """Dismiss whatever dialog is on screen, so the next test starts clean."""
    window = miaz.widget('window')
    for _attempt in range(4):
        dialog = window.get_visible_dialog()
        if dialog is None:
            return
        dialog.set_can_close(True)
        dialog.close()
        miaz.pump(0.3)


def run_export(miaz, plugin, target_dir, pattern='', readable=False):
    """Open the dialog, fill it in, and press Apply."""
    plugin.export()
    miaz.pump(0.3)
    plugin.target_dir = target_dir
    plugin.chkPattern.set_active(bool(pattern))
    if pattern:
        plugin.etyPattern.set_text(pattern)
    plugin.chkReadable.set_active(readable)
    plugin._on_dialog_response(None, 'apply', None)
    miaz.pump(0.3)


def exported_files(target_dir):
    found = []
    for root, _dirs, names in os.walk(target_dir):
        for name in names:
            found.append(os.path.relpath(os.path.join(root, name), target_dir))
    return sorted(found)


def test_the_documents_reach_the_target_folder(miaz, export2dir, tmp_path):
    target = str(tmp_path / 'plain')
    os.makedirs(target)
    selected = len(miaz.workspace.get_selected_items())

    run_export(miaz, export2dir, target)
    miaz.wait_until(lambda: len(exported_files(target)) == selected,
                    message='the documents were copied')
    dialogs_closed(miaz)

    for name in exported_files(target):
        assert name.endswith('.pdf')


def test_the_pattern_builds_the_directories(miaz, export2dir, tmp_path):
    target = str(tmp_path / 'tree')
    os.makedirs(target)
    selected = len(miaz.workspace.get_selected_items())

    run_export(miaz, export2dir, target, pattern='CY')
    miaz.wait_until(lambda: len(exported_files(target)) == selected,
                    message='the documents were copied')
    dialogs_closed(miaz)

    for name in exported_files(target):
        country, year, _basename = name.split(os.sep)
        assert len(country) == 2, name
        assert year.isdigit() and len(year) == 4, name


def test_readable_names_carry_the_descriptions(miaz, export2dir, tmp_path):
    target = str(tmp_path / 'readable')
    os.makedirs(target)
    selected = len(miaz.workspace.get_selected_items())

    run_export(miaz, export2dir, target, readable=True)
    miaz.wait_until(lambda: len(exported_files(target)) == selected,
                    message='the documents were copied')
    dialogs_closed(miaz)

    names = exported_files(target)
    assert all(name.startswith('20') and ' - ' in name for name in names), names
    # The sandbox describes every value, so no key survives in the name.
    assert not any('BANKX' in name or 'JOHNDOE' in name for name in names), names


def test_a_missing_target_folder_stops_the_export(miaz, export2dir):
    """os.path.exists(None) used to raise here, with the dialog still open."""
    export2dir.export()
    miaz.pump(0.3)
    export2dir.target_dir = None
    export2dir._on_dialog_response(None, 'apply', None)
    miaz.pump(0.3)
    dialogs_closed(miaz)


def test_a_pattern_letter_that_means_nothing_stops_the_export(miaz, export2dir, tmp_path):
    """An unknown letter used to raise halfway through the copy."""
    target = str(tmp_path / 'bad-pattern')
    os.makedirs(target)

    run_export(miaz, export2dir, target, pattern='Cz')
    miaz.pump(0.5)
    dialogs_closed(miaz)

    assert exported_files(target) == []


def test_the_folder_and_the_pattern_are_remembered(miaz, export2dir, tmp_path):
    target = str(tmp_path / 'remembered')
    os.makedirs(target)
    selected = len(miaz.workspace.get_selected_items())

    run_export(miaz, export2dir, target, pattern='G', readable=True)
    miaz.wait_until(lambda: len(exported_files(target)) == selected,
                    message='the documents were copied')
    dialogs_closed(miaz)

    settings = export2dir.get_settings()
    assert settings == {'target_dir': target, 'pattern': 'G',
                        'use_pattern': True, 'readable': True}

    # And the next dialog opens with them already filled in.
    export2dir.export()
    miaz.pump(0.3)
    assert export2dir.target_dir == target
    assert export2dir.etyPattern.get_text() == 'G'
    assert export2dir.chkPattern.get_active() is True
    assert export2dir.chkReadable.get_active() is True
    export2dir._on_dialog_response(None, 'cancel', None)
    miaz.pump(0.3)
    dialogs_closed(miaz)
