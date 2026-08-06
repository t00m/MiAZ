#!/usr/bin/python3

"""
Tests for MiAZ.backend.gate.UpdateGate.

This replaces MiAZStatus.BUSY as the "do not refresh the view" flag. That flag
was process-wide, set from six places (four of them plugins) and reset
unconditionally by each, so two overlapping operations left the first one to
finish clearing it while the second was still running.
"""

import pytest

from MiAZ.backend.gate import UpdateGate


class Recorder:
    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1


@pytest.fixture
def released():
    return Recorder()


@pytest.fixture
def gate(released):
    return UpdateGate(released)


# ---------------------------------------------------------------------------
# request()
# ---------------------------------------------------------------------------

def test_an_update_runs_when_nothing_is_suspended(gate):
    assert gate.request() is True


def test_an_update_is_held_while_suspended(gate):
    gate.suspend()
    assert gate.request() is False


def test_updates_run_again_after_the_release(gate):
    handle = gate.suspend()
    handle.release()
    assert gate.request() is True


# ---------------------------------------------------------------------------
# Release
# ---------------------------------------------------------------------------

def test_a_held_update_runs_on_release(gate, released):
    handle = gate.suspend()
    gate.request()
    assert released.calls == 0
    handle.release()
    assert released.calls == 1


def test_release_does_nothing_when_no_update_was_wanted(gate, released):
    gate.suspend().release()
    assert released.calls == 0


def test_many_held_updates_collapse_into_one(gate, released):
    handle = gate.suspend()
    for _ in range(10):
        gate.request()
    handle.release()
    assert released.calls == 1


# ---------------------------------------------------------------------------
# Overlap: the bug MiAZStatus.BUSY could not express
# ---------------------------------------------------------------------------

def test_two_overlapping_holders_keep_the_gate_shut(gate):
    """Two plugins working at once. The first to finish must not reopen it."""
    first = gate.suspend()
    second = gate.suspend()
    first.release()
    assert gate.is_suspended() is True
    assert gate.request() is False


def test_the_update_runs_once_when_the_last_holder_releases(gate, released):
    first = gate.suspend()
    second = gate.suspend()
    gate.request()
    first.release()
    assert released.calls == 0
    second.release()
    assert released.calls == 1


def test_releasing_out_of_order_is_fine(gate, released):
    first = gate.suspend()
    second = gate.suspend()
    gate.request()
    second.release()
    first.release()
    assert released.calls == 1


# ---------------------------------------------------------------------------
# The handle
# ---------------------------------------------------------------------------

def test_the_handle_works_as_a_context_manager(gate, released):
    with gate.suspend():
        assert gate.request() is False
    assert released.calls == 1


def test_leaving_the_block_through_an_exception_still_releases(gate):
    with pytest.raises(ValueError):
        with gate.suspend():
            raise ValueError('boom')
    assert gate.is_suspended() is False


def test_releasing_twice_does_not_open_the_gate_early(gate):
    """A caller that both uses the context manager and calls release() must not
    take the count below the number of real holders.
    """
    first = gate.suspend()
    second = gate.suspend()
    first.release()
    first.release()
    assert gate.is_suspended() is True


def test_release_reports_whether_it_did_anything(gate):
    handle = gate.suspend()
    assert handle.release() is True
    assert handle.release() is False


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------

def test_a_failing_callback_leaves_the_gate_open(gate):
    """The old flag stayed BUSY for good when anything raised between the two
    set_status calls. Nothing may leave this gate shut.
    """
    def boom():
        raise RuntimeError('no good')

    gate = UpdateGate(boom)
    handle = gate.suspend()
    gate.request()
    with pytest.raises(RuntimeError):
        handle.release()
    assert gate.is_suspended() is False
    assert gate.request() is True


def test_is_suspended_tracks_the_depth(gate):
    assert gate.is_suspended() is False
    first = gate.suspend()
    assert gate.is_suspended() is True
    second = gate.suspend()
    first.release()
    assert gate.is_suspended() is True
    second.release()
    assert gate.is_suspended() is False
