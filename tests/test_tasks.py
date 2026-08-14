#!/usr/bin/python3

"""
Tests for MiAZ.backend.tasks — background work with the result marshalled back
onto the main loop.

No mocks: the callbacks are delivered through the real GLib main context, which
the tests pump by hand instead of running a full MiAZ main loop.
"""

import logging
import threading
import time

import gi
gi.require_version('GLib', '2.0')

from gi.repository import GLib

import pytest

from MiAZ.backend.tasks import log as tasks_log
from MiAZ.backend.tasks import run_in_background


def pump_until(event, timeout=5.0):
    """Iterate the default main context until event fires, or give up.

    GLib.idle_add callbacks only run when something drives the main context.
    Doing it here rather than starting a MainLoop keeps a failing test to a
    timeout instead of a hang.
    """
    deadline = time.monotonic() + timeout
    while not event.is_set() and time.monotonic() < deadline:
        while GLib.MainContext.default().pending():
            GLib.MainContext.default().iteration(False)
        time.sleep(0.005)
    return event.is_set()


@pytest.fixture(autouse=True)
def drain_main_context():
    """Leave no pending callback behind to fire during another test."""
    yield
    while GLib.MainContext.default().pending():
        GLib.MainContext.default().iteration(False)


def test_the_work_runs_off_the_calling_thread():
    seen = {}
    done = threading.Event()

    def work():
        seen['thread'] = threading.current_thread().name

    run_in_background(work, on_done=lambda _r: done.set())
    assert pump_until(done)
    assert seen['thread'] != threading.current_thread().name


def test_on_done_receives_the_return_value():
    result = {}
    done = threading.Event()

    def capture(value):
        result['value'] = value
        done.set()

    run_in_background(lambda: 21 * 2, on_done=capture)
    assert pump_until(done)
    assert result['value'] == 42


def test_on_done_runs_on_the_main_thread():
    """The whole point: the callback can touch widgets safely."""
    seen = {}
    done = threading.Event()

    def capture(_value):
        seen['thread'] = threading.current_thread().name
        done.set()

    run_in_background(lambda: None, on_done=capture)
    assert pump_until(done)
    assert seen['thread'] == threading.current_thread().name


def test_on_error_receives_the_exception():
    caught = {}
    done = threading.Event()

    def capture(error):
        caught['error'] = error
        done.set()

    def boom():
        raise ValueError('no good')

    run_in_background(boom, on_error=capture)
    assert pump_until(done)
    assert isinstance(caught['error'], ValueError)
    assert str(caught['error']) == 'no good'


def test_on_done_is_not_called_when_the_work_raises():
    calls = []
    done = threading.Event()

    def boom():
        raise ValueError('no good')

    run_in_background(
        boom,
        on_done=lambda _r: calls.append('done'),
        on_error=lambda _e: done.set())
    assert pump_until(done)
    assert calls == []


class RecordingHandler(logging.Handler):
    """Captures records straight off the tasks logger.

    pytest's caplog attaches to the Python root logger, which never sees
    these: MiAZ loggers hang off the 'MiAZ' root, and that root does not
    propagate any further on purpose.
    """

    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


@pytest.fixture
def task_log():
    handler = RecordingHandler()
    tasks_log.addHandler(handler)
    yield handler
    tasks_log.removeHandler(handler)


def test_a_failure_without_an_error_handler_is_logged(task_log):
    """A raw thread that raises dies where nobody sees it. This must not."""
    thread = run_in_background(lambda: 1 / 0)
    thread.join(timeout=5)
    assert not thread.is_alive()
    messages = [record.getMessage() for record in task_log.records]
    assert any('division by zero' in message for message in messages), messages


def test_the_logged_failure_carries_the_traceback(task_log):
    """Without exc_info the log line says what broke but not where."""
    thread = run_in_background(lambda: 1 / 0)
    thread.join(timeout=5)
    assert any(record.exc_info is not None for record in task_log.records)


def test_a_failing_callback_is_logged_and_does_not_break_the_main_loop(task_log):
    """An exception inside on_done runs on the main loop, where an unhandled
    one would take the application down.
    """
    done = threading.Event()

    def bad_callback(_value):
        done.set()
        raise RuntimeError('callback exploded')

    run_in_background(lambda: None, on_done=bad_callback)
    assert pump_until(done)
    # The callback runs inside the idle source; give it a beat to be logged.
    for _ in range(20):
        if any('callback exploded' in r.getMessage() for r in task_log.records):
            break
        time.sleep(0.005)
    messages = [record.getMessage() for record in task_log.records]
    assert any('callback exploded' in message for message in messages), messages


def test_a_failure_without_an_error_handler_does_not_kill_the_thread():
    thread = run_in_background(lambda: 1 / 0)
    thread.join(timeout=5)
    assert not thread.is_alive()


def test_the_thread_is_a_daemon_so_it_never_blocks_shutdown():
    thread = run_in_background(lambda: None)
    assert thread.daemon is True
    thread.join(timeout=5)


def test_the_thread_can_be_named_for_the_log():
    thread = run_in_background(lambda: None, name='indexing')
    assert thread.name == 'indexing'
    thread.join(timeout=5)


def test_work_without_callbacks_still_runs():
    ran = threading.Event()
    thread = run_in_background(ran.set)
    thread.join(timeout=5)
    assert ran.is_set()
