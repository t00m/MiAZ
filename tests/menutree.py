#!/usr/bin/python3

"""Read the actions out of a Gio.Menu tree.

Shared by the UI tests that compare what the menus held before and after a
plugin was unloaded.
"""


def menu_actions(menu, seen=None, keep=None):
    """Every action reachable from `menu`, submenus and sections included.

    A menu linked from two places is walked once. The visited set is keyed on
    id(), so every wrapper visited is also held in `keep` for the length of the
    walk: get_item_link() builds a fresh Python wrapper each call, and a freed
    one leaves its address behind for the next sibling to reuse, which made the
    sibling look like a menu that had already been walked.
    """
    if seen is None:
        seen = set()
    if keep is None:
        keep = []
    if menu is None or id(menu) in seen:
        return []
    seen.add(id(menu))
    keep.append(menu)
    found = []
    for position in range(menu.get_n_items()):
        value = menu.get_item_attribute_value(position, 'action', None)
        if value is not None:
            found.append(value.get_string())
        for link in ('submenu', 'section'):
            child = menu.get_item_link(position, link)
            if child is not None:
                found.extend(menu_actions(child, seen, keep))
    return found
