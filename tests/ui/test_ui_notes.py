#!/usr/bin/python3

"""
Tests for the Notes service, which is core as of 0.3.

Notes is registered before the window is built, so it lives through the very
first repository switch with no workspace and no all-notes page. That ordering
is what these tests reproduce: the service is built while the workspace lookup
still answers None, exactly as it is at startup.
"""

import os

import pytest

from MiAZ.backend.notes import notes_dir
from MiAZ.frontend.desktop.services.notes import MiAZNotes


@pytest.fixture
def early_notes(miaz, monkeypatch):
    """A Notes service built before the workspace exists.

    The real one is registered in _on_activate, ahead of _setup_ui, so it sees
    no workspace and defers its startup to 'application-started'. The session
    application has already passed that point, so the copy built here never
    starts: that is the state under test.
    """
    app = miaz.app
    get_widget = app.get_widget
    monkeypatch.setattr(
        app, 'get_widget',
        lambda name, *args, **kwargs: (
            None if name == 'workspace' else get_widget(name, *args, **kwargs)))
    service = MiAZNotes(app)
    monkeypatch.undo()
    yield service
    # The copy stays connected to util, the repository and the watcher for as
    # long as the session application lives. Unhook it, so the tests that run
    # after this one have one Notes service reacting to their renames.
    for source, handlers in (
            (app.get_service('util'), (service._on_renamed, service._on_deleted,
                                       service._on_added)),
            (app.get_service('repo'), (service._on_repo_switched,)),
            (app.get_service('watcher'), (service._on_repo_updated,))):
        if source is None:
            continue
        for handler in handlers:
            try:
                source.disconnect_by_func(handler)
            except (TypeError, ValueError):
                pass


def test_the_service_has_no_all_notes_page_before_it_starts(early_notes):
    """Reading the attribute is what the repository switch does, so it has to
    exist from __init__ rather than from startup()."""
    assert early_notes.started() is False
    assert early_notes._all_notes is None


def test_switching_repository_before_the_workspace_exists_is_not_a_crash(
        early_notes, miaz, sandbox):
    """The first switch happens at startup, ahead of the workspace. Notes read
    its all-notes page there and raised AttributeError."""
    early_notes._on_repo_switched(miaz.service('repo'))
    miaz.pump(0.2)

    assert early_notes.store.data_dir == notes_dir(miaz.service('repo').docs)
    assert os.path.isdir(early_notes.store.data_dir)
