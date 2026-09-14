#!/usr/bin/python3

"""The menu walker the plugin cycle test leans on.

Gio.Menu needs no display, so this runs in the plain suite. It exists because
the walker used to key its visited set on id() of the wrapper objects
get_item_link() hands back. Those are freed as soon as the recursion returns,
CPython hands the same address to the next sibling, and the sibling was skipped
as already seen. Five of six submenus vanished.
"""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gio

from tests.menutree import menu_actions


def tree_of(count):
    """One root holding `count` submenus, each with one action."""
    root = Gio.Menu.new()
    for index in range(count):
        submenu = Gio.Menu.new()
        submenu.append_item(Gio.MenuItem.new(f'label{index}', f'app.act{index}'))
        root.append_submenu(f's{index}', submenu)
    return root


def test_every_sibling_submenu_is_walked():
    assert menu_actions(tree_of(6)) == [f'app.act{index}' for index in range(6)]


def test_a_section_is_walked_like_a_submenu():
    root = Gio.Menu.new()
    section = Gio.Menu.new()
    section.append_item(Gio.MenuItem.new('one', 'app.one'))
    section.append_item(Gio.MenuItem.new('two', 'app.two'))
    root.append_section(None, section)
    assert menu_actions(root) == ['app.one', 'app.two']


def test_a_menu_linked_twice_is_walked_once():
    """The plugin submenus hang from more than one root."""
    shared = Gio.Menu.new()
    shared.append_item(Gio.MenuItem.new('shared', 'app.shared'))
    root = Gio.Menu.new()
    root.append_submenu('first', shared)
    root.append_submenu('second', shared)
    assert menu_actions(root) == ['app.shared']


def test_nothing_is_not_an_error():
    assert menu_actions(None) == []
    assert menu_actions(Gio.Menu.new()) == []
