#!/usr/bin/python3

"""The keyboard shortcut registry and the core table.

Headless: the registry imports Gtk only for Gtk.accelerator_parse, which needs
no display. Keeping these tests out of tests/ui is deliberate, because this is
where a future collision gets caught cheaply.
"""

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


def test_only_the_five_bare_keys_are_list_scoped():
    """Scoping is the safety mechanism for keys a text entry also wants. If a
    sixth key becomes list scoped, that is a decision, not an accident.

    Escape joined this set because a global accelerator runs in the capture
    phase and would swallow Escape from Adw.AlertDialog, Adw.Dialog and
    Gtk.Popover before their own bubble phase handler ever saw it."""
    scoped = {action for _s, _l, action, _a, scope in sct.CORE
              if scope == sct.LIST}
    assert scoped == {'document-open', 'document-rename',
                      'document-delete', 'document-select-all',
                      'filters-clear'}


# The factory routes everything through the registry


class FakeApp:
    """Enough application for create_menuitem, and a record of what it set."""

    def __init__(self, registry=None):
        self._registry = registry
        self.accels = {}
        self.actions = []

    def get_service(self, name):
        return self._registry if name == 'shortcuts' else None

    def add_action(self, action):
        self.actions.append(action)

    def set_accels_for_action(self, detailed, shortcuts):
        self.accels[detailed] = list(shortcuts)


def factory_for(app):
    from MiAZ.frontend.desktop.services.factory import MiAZFactory
    return MiAZFactory(app)


def test_the_factory_sets_an_accelerator_the_registry_granted():
    registry = make()
    app = FakeApp(registry)
    factory_for(app).create_menuitem('a-thing', 'A thing', lambda *a: None,
                                     None, ['<Control>j'])
    assert app.accels['app.a-thing'] == ['<Control>j']
    assert [b.action for b in registry.bindings()] == ['a-thing']


def test_the_factory_does_not_set_an_accelerator_the_registry_refused():
    """This is the whole point. A refused key must not reach GTK, or the
    registry would be bookkeeping while the collision happened anyway."""
    registry = make()
    registry.register('core', 'app-quit', '<Control>q')
    app = FakeApp(registry)
    factory_for(app).create_menuitem('greedy', 'Greedy', lambda *a: None,
                                     None, ['<Control>q'])
    assert 'app.greedy' not in app.accels
    assert registry.conflicts()[0]['action'] == 'greedy'


def test_a_refused_entry_still_becomes_a_working_menu_item():
    """Losing the key must not lose the command."""
    registry = make()
    registry.register('core', 'app-quit', '<Control>q')
    app = FakeApp(registry)
    item = factory_for(app).create_menuitem('greedy', 'Greedy',
                                            lambda *a: None, None,
                                            ['<Control>q'])
    assert item is not None
    assert len(app.actions) == 1


def test_the_owner_is_recorded_so_a_plugin_can_give_its_keys_back():
    registry = make()
    app = FakeApp(registry)
    factory_for(app).create_menuitem('p-thing', 'Thing', lambda *a: None,
                                     None, ['<Control>j'], owner='MiAZThing')
    registry.unregister_owner('MiAZThing')
    assert registry.bindings() == []


def test_create_menu_action_goes_through_the_registry_too():
    registry = make()
    app = FakeApp(registry)
    factory_for(app).create_menu_action('an-action', lambda *a: None,
                                        ['<Control>j'])
    assert app.accels['app.an-action'] == ['<Control>j']
    assert [b.action for b in registry.bindings()] == ['an-action']


def test_without_a_registry_the_factory_behaves_as_it_always_did():
    """The console frontend installs no registry, and neither do several
    existing tests. Both must keep working."""
    app = FakeApp(None)
    factory_for(app).create_menuitem('a-thing', 'A thing', lambda *a: None,
                                     None, ['<Control>j'])
    assert app.accels['app.a-thing'] == ['<Control>j']


# Lifecycle


def test_a_plugin_unloading_frees_its_keys_for_the_next_load():
    """Disable a plugin, enable it again, and its key must still work.

    The `bindings() == []` assertion right after unregister_owner is the real
    proof: it shows the binding is genuinely released, not merely tolerated.
    register() treats a reclaim by the same owner of the same action as
    idempotent and grants it either way, so the second create_menuitem call
    succeeding would look identical whether or not the key had actually been
    freed. Genuine release is what would let a DIFFERENT owner claim the key
    afterward; this test happens to reclaim with the same owner, but the empty
    bindings() list is what rules out the false alternative that the key was
    simply left held."""
    registry = make()
    app = FakeApp(registry)
    factory = factory_for(app)
    factory.create_menuitem('p-thing', 'Thing', lambda *a: None, None,
                            ['<Control>j'], owner='MiAZThing')
    registry.unregister_owner('MiAZThing')
    assert registry.bindings() == []
    factory.create_menuitem('p-thing', 'Thing', lambda *a: None, None,
                            ['<Control>j'], owner='MiAZThing')
    assert registry.conflicts() == []
    assert app.accels['app.p-thing'] == ['<Control>j']


# No accelerator is written down anywhere but the table


import ast
import os


SOURCE_ROOTS = ('MiAZ', 'data/resources/plugins')
# The registry itself holds the table, and the plugin that keeps its own three
# keys. Everything else must ask the registry.
ALLOWED = {
    os.path.join('MiAZ', 'frontend', 'desktop', 'services', 'shortcuts.py'),
    os.path.join('data', 'resources', 'plugins', 'MiAZProjectMgt', 'projmgt.py'),
}


def python_sources():
    for root in SOURCE_ROOTS:
        for base, dirs, names in os.walk(root):
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for name in names:
                if name.endswith('.py'):
                    yield os.path.join(base, name)


def accelerator_literals(path):
    """Every string constant that GTK reads as a real key combination."""
    with open(path, encoding='utf-8') as source:
        tree = ast.parse(source.read(), filename=path)
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        text = node.value
        if not text.startswith('<'):
            continue
        ok, key, mods = Gtk.accelerator_parse(text)
        if ok and key != 0:
            found.append(text)
    return found


def test_no_accelerator_is_written_outside_the_table():
    """A literal accelerator somewhere else is a second source of truth, and
    a second source of truth is the bug this whole design removes."""
    offenders = {}
    for path in python_sources():
        if path in ALLOWED:
            continue
        literals = accelerator_literals(path)
        if literals:
            offenders[path] = literals
    assert offenders == {}, (
        f"these files hold accelerators the registry never sees: {offenders}")
