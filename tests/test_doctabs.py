#!/usr/bin/python3

"""
Tests for the document-tabs registry, the seam plugins use to contribute a tab
to the single-document rename dialog.

The registry holds no widgets, so this runs headless: the gi versions are set
before importing, the same way tests/test_util.py does.
"""

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

import pytest  # noqa: E402

from MiAZ.frontend.desktop.services.doctabs import MiAZDocumentTabs  # noqa: E402


class FakeApp:
    """Enough of the app for the registry: it only keeps a reference."""


@pytest.fixture
def tabs():
    return MiAZDocumentTabs(FakeApp())


def widget_factory(_app):
    return object()


def test_registration_is_returned(tabs):
    tabs.register(owner='MiAZProjectMgt', name='projects', title='Projects',
                  factory=widget_factory)
    registrations = tabs.get_registrations()
    assert len(registrations) == 1
    assert registrations[0]['owner'] == 'MiAZProjectMgt'
    assert registrations[0]['name'] == 'projects'
    assert registrations[0]['title'] == 'Projects'
    assert registrations[0]['factory'] is widget_factory
    assert registrations[0]['weight'] == 100


def test_registrations_are_ordered_by_weight_then_title(tabs):
    tabs.register(owner='c', name='c', title='Zeta', factory=widget_factory, weight=100)
    tabs.register(owner='a', name='a', title='Alpha', factory=widget_factory, weight=300)
    tabs.register(owner='b', name='b', title='Beta', factory=widget_factory, weight=100)
    assert [tab['name'] for tab in tabs.get_registrations()] == ['b', 'c', 'a']


def test_registering_the_same_name_replaces_it(tabs):
    tabs.register(owner='MiAZProjectMgt', name='projects', title='Projects',
                  factory=widget_factory)
    tabs.register(owner='MiAZProjectMgt', name='projects', title='Projects',
                  factory=widget_factory)
    # A plugin that activates twice must not contribute the tab twice.
    assert tabs.count() == 1


def test_a_factory_that_is_not_callable_is_refused(tabs):
    tabs.register(owner='broken', name='broken', title='Broken', factory=None)
    assert tabs.count() == 0


def test_unregister_by_name(tabs):
    tabs.register(owner='MiAZProjectMgt', name='projects', title='Projects',
                  factory=widget_factory)
    tabs.unregister('projects')
    assert tabs.get_registrations() == []
    # Unregistering something that is not there is not an error.
    tabs.unregister('projects')


def test_unregister_all_only_drops_that_owner(tabs):
    tabs.register(owner='MiAZProjectMgt', name='projects', title='Projects',
                  factory=widget_factory)
    tabs.register(owner='MiAZProjectMgt', name='budget', title='Budget',
                  factory=widget_factory)
    tabs.register(owner='MiAZPeriodicity', name='periodicity', title='Periodicity',
                  factory=widget_factory)
    tabs.unregister_all('MiAZProjectMgt')
    assert [tab['name'] for tab in tabs.get_registrations()] == ['periodicity']


def test_icon_name_is_optional(tabs):
    tabs.register(owner='a', name='a', title='A', factory=widget_factory)
    tabs.register(owner='b', name='b', title='B', factory=widget_factory,
                  icon_name='some-symbolic')
    icons = {tab['name']: tab['icon_name'] for tab in tabs.get_registrations()}
    assert icons == {'a': None, 'b': 'some-symbolic'}
