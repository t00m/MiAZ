#!/usr/bin/python3

"""The keyboard shortcut registry and the core table.

Headless: the registry imports Gtk only for Gtk.accelerator_parse, which needs
no display. Keeping these tests out of tests/ui is deliberate, because this is
where a future collision gets caught cheaply.
"""

import pytest

from gi.repository import Gtk

from MiAZ.frontend.desktop.services import shortcuts as sct


def make():
    return sct.MiAZShortcuts()


def parsed(accelerator):
    ok, key, mods = Gtk.accelerator_parse(accelerator)
    assert ok, f"{accelerator} does not parse"
    return key, mods


# The registry


def test_a_free_accelerator_is_granted():
    registry = make()
    assert registry.register('core', 'app-quit', '<Control>q') is True


def test_the_second_claim_on_one_accelerator_is_refused():
    """First wins. Core registers before any plugin loads, so a plugin can
    never take a key out from under the application."""
    registry = make()
    registry.register('core', 'app-quit', '<Control>q')
    assert registry.register('MiAZPlugin', 'plugin-thing', '<Control>q') is False
    held = registry.bindings()
    assert [b.action for b in held] == ['app-quit']


def test_a_refusal_is_reported_with_both_owners():
    registry = make()
    registry.register('core', 'app-quit', '<Control>q')
    registry.register('MiAZPlugin', 'plugin-thing', '<Control>q')
    conflicts = registry.conflicts()
    assert len(conflicts) == 1
    assert conflicts[0]['owner'] == 'MiAZPlugin'
    assert conflicts[0]['action'] == 'plugin-thing'
    assert conflicts[0]['held_by'] == 'core'
    assert conflicts[0]['held_action'] == 'app-quit'


def test_the_same_claim_twice_is_still_one():
    """Menus are rebuilt whenever plugins load, so the same owner registering
    the same action on the same key is normal and must not be a conflict."""
    registry = make()
    assert registry.register('core', 'app-quit', '<Control>q') is True
    assert registry.register('core', 'app-quit', '<Control>q') is True
    assert registry.conflicts() == []
    assert len(registry.bindings()) == 1


def test_two_spellings_of_one_key_are_one_key():
    """The codebase contains both '<Ctrl>N' and '<Control>n'. Comparing the
    strings would call them different keys and let a real collision through."""
    registry = make()
    registry.register('core', 'notes-doc', '<Control>n')
    assert registry.register('Other', 'other', '<Ctrl>N') is False


def test_an_unparsable_accelerator_is_refused():
    registry = make()
    assert registry.register('core', 'nonsense', 'not-an-accelerator') is False
    assert registry.bindings() == []


def test_unregister_owner_frees_its_keys_for_a_later_claim():
    registry = make()
    registry.register('MiAZPlugin', 'plugin-thing', '<Control>j')
    registry.unregister_owner('MiAZPlugin')
    assert registry.bindings() == []
    assert registry.register('Another', 'another', '<Control>j') is True


def test_unregister_owner_leaves_other_owners_alone():
    registry = make()
    registry.register('core', 'app-quit', '<Control>q')
    registry.register('MiAZPlugin', 'plugin-thing', '<Control>j')
    registry.unregister_owner('MiAZPlugin')
    assert [b.action for b in registry.bindings()] == ['app-quit']


def test_accelerators_for_returns_only_global_scope():
    """A list scoped key is installed on the document list, not on the
    application, so a call site asking what to pass to set_accels_for_action
    must not be given it."""
    registry = make()
    registry.register('core', 'app-quit', '<Control>q', scope=sct.GLOBAL)
    registry.register('core', 'document-delete', 'Delete', scope=sct.LIST)
    assert registry.accelerators_for('app-quit') == ['<Control>q']
    assert registry.accelerators_for('document-delete') == []


def test_accelerators_for_an_unknown_action_is_empty():
    assert make().accelerators_for('nothing-like-this') == []


def test_bindings_can_be_filtered_by_scope():
    registry = make()
    registry.register('core', 'app-quit', '<Control>q', scope=sct.GLOBAL)
    registry.register('core', 'document-delete', 'Delete', scope=sct.LIST)
    assert [b.action for b in registry.bindings(scope=sct.LIST)] == ['document-delete']


def test_bindings_come_back_in_section_order():
    registry = make()
    registry.register('p', 'plugin-thing', '<Control>j', section=sct.SECTION_PLUGINS)
    registry.register('core', 'app-quit', '<Control>q', section=sct.SECTION_APPLICATION)
    registry.register('core', 'view-grid', '<Control>2', section=sct.SECTION_VIEWS)
    assert [b.section for b in registry.bindings()] == [
        sct.SECTION_APPLICATION, sct.SECTION_VIEWS, sct.SECTION_PLUGINS]


# The core table


def test_register_core_loads_the_whole_table_without_a_conflict():
    registry = make()
    registry.register_core()
    assert registry.conflicts() == []
    assert len(registry.bindings()) == len(sct.CORE)


def test_every_core_accelerator_parses():
    for _section, _label, action, accelerator, _scope in sct.CORE:
        ok, _key, _mods = Gtk.accelerator_parse(accelerator)
        assert ok, f"{action} has an accelerator GTK cannot parse: {accelerator}"


def test_no_two_core_entries_claim_the_same_key():
    seen = {}
    for _section, _label, action, accelerator, _scope in sct.CORE:
        key = parsed(accelerator)
        assert key not in seen, (
            f"{action} and {seen[key]} both claim {accelerator}")
        seen[key] = action


def test_no_core_entry_uses_a_reserved_combination():
    """The combinations the desktop or a GTK text entry already owns. This is
    the test that fails if someone binds Ctrl+BackSpace again."""
    reserved = {parsed(item) for item in sct.RESERVED}
    for _section, _label, action, accelerator, _scope in sct.CORE:
        assert parsed(accelerator) not in reserved, (
            f"{action} takes {accelerator}, which the desktop already owns")


def test_every_core_entry_has_a_known_scope():
    for _section, _label, action, _accelerator, scope in sct.CORE:
        assert scope in (sct.GLOBAL, sct.LIST), f"{action} has scope {scope}"


def test_every_core_entry_has_a_known_section():
    for section, _label, action, _accelerator, _scope in sct.CORE:
        assert section in sct.SECTION_ORDER, f"{action} has section {section}"


def test_core_action_names_are_unique():
    names = [row[2] for row in sct.CORE]
    assert len(names) == len(set(names))


def test_only_the_four_bare_keys_are_list_scoped():
    """Scoping is the safety mechanism for keys a text entry also wants. If a
    fifth key becomes list scoped, that is a decision, not an accident."""
    scoped = {action for _s, _l, action, _a, scope in sct.CORE
              if scope == sct.LIST}
    assert scoped == {'document-open', 'document-rename',
                      'document-delete', 'document-select-all'}
