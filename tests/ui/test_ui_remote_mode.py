#!/usr/bin/python3

"""UI: what a repository marked remote takes away, and gives back."""

import pytest


@pytest.fixture
def local_again(miaz):
    """Always hand the session fixture back a local repository.

    The miaz fixture is session scoped, so a test that left the flag on would
    blind every test after it.
    """
    yield miaz
    miaz.service('repo').set_remote(False)
    miaz.pump(0.4)


def test_thumbnail_views_are_gone_when_remote(local_again):
    """Grid, timeline and conversation each render one thumbnail per row."""
    workspace = local_again.workspace

    local_again.service('repo').set_remote(True)
    local_again.pump(0.4)

    assert 'grid' not in workspace._view_buttons
    assert 'timeline' not in workspace._view_buttons
    assert 'conversation' not in workspace._view_buttons


def test_the_cheap_views_survive(local_again):
    """Details and filenames read nothing but the index, so they stay."""
    workspace = local_again.workspace

    local_again.service('repo').set_remote(True)
    local_again.pump(0.4)

    assert 'details' in workspace._view_buttons
    assert 'filenames' in workspace._view_buttons


def test_show_view_grid_lands_on_details_when_remote(local_again):
    """A plugin calling show_view('grid') gets what the toolbar would give."""
    workspace = local_again.workspace
    local_again.service('repo').set_remote(True)
    local_again.pump(0.4)

    workspace.show_view('grid')
    local_again.pump(0.3)

    assert workspace._view_stack.get_visible_child_name() == 'details'


def test_unmarking_restores_the_views_without_a_restart(local_again):
    """Hard disable means the switch is the only way back."""
    workspace = local_again.workspace
    local_again.service('repo').set_remote(True)
    local_again.pump(0.4)
    assert 'grid' not in workspace._view_buttons

    local_again.service('repo').set_remote(False)
    local_again.pump(0.4)

    assert 'grid' in workspace._view_buttons
    workspace.show_view('grid')
    local_again.pump(0.3)
    assert workspace._view_stack.get_visible_child_name() == 'grid'


def test_marking_remote_moves_off_a_disabled_view(local_again):
    """The user is looking at the grid when the switch goes on."""
    workspace = local_again.workspace
    workspace.show_view('grid')
    local_again.pump(0.3)
    assert workspace._view_stack.get_visible_child_name() == 'grid'

    local_again.service('repo').set_remote(True)
    local_again.pump(0.4)

    assert workspace._view_stack.get_visible_child_name() == 'details'


def test_a_surviving_view_is_kept_across_the_switch(local_again):
    """Filenames is not disabled, so marking remote must not yank the user
    back to Details for no reason."""
    workspace = local_again.workspace
    workspace.show_view('filenames')
    local_again.pump(0.3)

    local_again.service('repo').set_remote(True)
    local_again.pump(0.4)

    assert workspace._view_stack.get_visible_child_name() == 'filenames'


def test_review_mode_starts_no_duplicate_scan_when_remote(local_again):
    """222.5 MB on the test repository, and nobody asked for it."""
    workspace = local_again.workspace
    local_again.service('repo').set_remote(True)
    local_again.pump(0.3)

    assert workspace._scan_duplicates() is False


def test_the_duplicate_scan_still_runs_when_local(local_again):
    """The gate must not disable the scan for everyone."""
    workspace = local_again.workspace
    index = local_again.service('index')
    index._invalidate_duplicates()

    assert workspace._scan_duplicates() is True
    local_again.pump(0.6)
