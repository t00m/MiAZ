#!/usr/bin/python3

"""What a recycled row and a coalesced refresh must do.

A Gtk.SignalListItemFactory builds its widget once in 'setup' and hands the
same widget to every item that scrolls into that slot, so anything 'bind' sets
for one item has to be unset for the next. The refresh tests guard the other
half of the same concern: one user action, one rebuild.
"""

from MiAZ.backend.models import MiAZItem
from MiAZ.frontend.desktop.widgets.chip import MiAZChip


class FakeListItem:
    """The three calls the factory callbacks make on a Gtk.ListItem."""

    def __init__(self):
        self._child = None
        self._item = None

    def set_child(self, child):
        self._child = child

    def get_child(self):
        return self._child

    def get_item(self):
        return self._item


def _recycle(view, *items):
    """Bind each item in turn to one recycled row, as scrolling does."""
    list_item = FakeListItem()
    view._on_factory_setup_subtitle(None, list_item)
    for item in items:
        list_item._item = item
        view._on_factory_bind_subtitle(None, list_item)
    return list_item.get_child().get_first_child()


def test_a_row_that_showed_an_inactive_document_does_not_stay_destructive(miaz):
    view = miaz.widget('workspace-view')
    inactive = MiAZItem(id='inactive.pdf', subtitle='inactive', active=False)
    active = MiAZItem(id='active.pdf', subtitle='active', active=True)

    label = _recycle(view, inactive, active)

    assert not label.has_css_class('destructive-action')


def test_an_inactive_document_is_still_marked_destructive(miaz):
    view = miaz.widget('workspace-view')
    inactive = MiAZItem(id='inactive.pdf', subtitle='inactive', active=False)

    label = _recycle(view, inactive)

    assert label.has_css_class('destructive-action')


def _count_chips(monkeypatch):
    """Count every MiAZChip built from now on.

    Counting the chips rather than the calls to _update_filter_tags is not a
    detour: the handlers are connected as bound methods, so replacing the
    method on the class leaves the signal connections calling the original and
    only the one direct call is seen. The chips are built through the class at
    call time, so this counts every rebuild.
    """
    built = []
    original = MiAZChip.__init__

    def probe(self, *args, **kwargs):
        built.append(1)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(MiAZChip, '__init__', probe)
    return built


def _tags_on_screen(workspace):
    count = 0
    child = workspace._filter_tags_flowbox.get_first_child()
    while child is not None:
        count += 1
        child = child.get_next_sibling()
    return count


def test_one_filter_change_builds_each_filter_tag_once(miaz, clean_view,
                                                       monkeypatch):
    workspace = miaz.workspace
    built = _count_chips(monkeypatch)

    miaz.select_dropdown_value('Country', 'ES')
    miaz.pump(1.0)

    shown = _tags_on_screen(workspace)
    assert shown > 0, 'the filter was not applied, so nothing was measured'
    assert len(built) == shown, f'built {len(built)} tags to show {shown}'


def test_clearing_the_filters_updates_the_dropdowns_once(miaz, clean_view,
                                                         monkeypatch):
    workspace = miaz.workspace
    miaz.select_dropdown_value('Country', 'ES')
    miaz.pump(0.5)

    calls = []
    original = type(workspace)._update_dropdowns_after_filter

    def probe(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(type(workspace), '_update_dropdowns_after_filter', probe)

    workspace.clear_filters()
    miaz.pump(1.0)

    assert len(calls) == 1, f'narrowed the dropdowns {len(calls)} times'
