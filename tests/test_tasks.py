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

from MiAZ.backend import tasks
from MiAZ.backend.tasks import log as tasks_log
from MiAZ.backend.tasks import run_in_background
from MiAZ.backend.tasks import run_on_main


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


def pump(iterations=200):
    """Iterate the main context a fixed number of times.

    A repeating idle source keeps the context busy forever, so this counts
    iterations instead of draining until nothing is pending.
    """
    context = GLib.MainContext.default()
    for _ in range(iterations):
        context.iteration(False)


def test_run_on_main_runs_a_callback_that_returns_a_value_only_once():
    """The bug this exists to stop.

    GLib repeats an idle source until the callback returns something falsy.
    MiAZDialog.show_toast returns the Adw.Toast it created, so
    GLib.idle_add(srvdlg.show_toast, msg) never lets go: the toast is
    recreated on every iteration of the main loop, forever.
    """
    calls = []

    def returns_a_toast(message):
        calls.append(message)
        return object()

    run_on_main(returns_a_toast, 'scanned and imported')
    pump()
    assert calls == ['scanned and imported']


def test_run_on_main_passes_every_argument_through():
    seen = {}

    def capture(*args, **kwargs):
        seen['args'] = args
        seen['kwargs'] = kwargs
        return True

    run_on_main(capture, 'a', 'b', timeout=5)
    pump()
    assert seen['args'] == ('a', 'b')
    assert seen['kwargs'] == {'timeout': 5}


def test_run_on_main_runs_on_the_main_thread():
    seen = {}

    def capture():
        seen['thread'] = threading.current_thread().name

    run_on_main(capture)
    pump()
    assert seen['thread'] == threading.current_thread().name


def test_a_raising_callback_is_logged_and_still_not_repeated(task_log):
    """An exception must not leave the source armed either."""
    calls = []

    def boom():
        calls.append(1)
        raise RuntimeError('toast exploded')

    run_on_main(boom)
    pump()
    assert calls == [1]
    messages = [record.getMessage() for record in task_log.records]
    assert any('toast exploded' in message for message in messages), messages


# ---------------------------------------------------------------------------
# Every background job registers itself, so nothing has to remember to
# ---------------------------------------------------------------------------

class RecordingQueue:
    """A stand-in for MiAZJobQueue that records what it was told."""

    def __init__(self):
        self.added = []
        self.started = []
        self.finished = []
        self.reports = []

    def add(self, name, label=None, queued=False):
        job = {'name': name, 'label': label, 'queued': queued}
        self.added.append(job)
        return job

    def start(self, job):
        self.started.append(job)

    def report(self, job, message, fraction=None):
        self.reports.append((message, fraction))

    def finish(self, job, error=None):
        self.finished.append((job, error))


def drain():
    """Run whatever run_in_background handed to the main loop."""
    context = GLib.MainContext.default()
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        while context.pending():
            context.iteration(False)
        time.sleep(0.01)


def test_a_background_job_registers_with_the_queue():
    """All 20 call sites already pass name=, so registering here is what puts
    every one of them in the indicator without editing any of them."""
    queue = RecordingQueue()
    tasks.set_job_queue(queue)
    try:
        thread = tasks.run_in_background(lambda: 'ok', name='importdoc-batch')
        thread.join(timeout=5)
        drain()
    finally:
        tasks.set_job_queue(None)
    assert queue.added and queue.added[0]['name'] == 'importdoc-batch'
    assert queue.started
    assert queue.finished and queue.finished[0][1] is None


def test_a_failing_job_is_finished_with_its_error():
    queue = RecordingQueue()
    tasks.set_job_queue(queue)

    def boom():
        raise OSError('the disk is full')

    try:
        thread = tasks.run_in_background(boom, on_error=lambda error: None,
                                         name='importdoc-batch')
        thread.join(timeout=5)
        drain()
    finally:
        tasks.set_job_queue(None)
    assert queue.finished
    assert isinstance(queue.finished[0][1], OSError)


def test_a_job_that_wants_to_report_is_given_a_reporter():
    queue = RecordingQueue()
    tasks.set_job_queue(queue)

    def work(report):
        report('340 of 1322', 0.257)
        return 'ok'

    try:
        thread = tasks.run_in_background(work, name='importdoc-batch')
        thread.join(timeout=5)
        drain()
    finally:
        tasks.set_job_queue(None)
    assert queue.reports == [('340 of 1322', 0.257)]


def test_work_that_takes_no_arguments_is_called_with_none():
    """Nineteen of the twenty call sites pass a plain lambda."""
    queue = RecordingQueue()
    tasks.set_job_queue(queue)
    seen = []
    try:
        thread = tasks.run_in_background(lambda: seen.append(True),
                                         name='workspace-scan')
        thread.join(timeout=5)
        drain()
    finally:
        tasks.set_job_queue(None)
    assert seen == [True]


def test_without_a_queue_nothing_changes():
    """The console frontend installs no queue, and the headless suite runs
    without one. Both must behave exactly as before."""
    tasks.set_job_queue(None)
    done = []
    thread = tasks.run_in_background(lambda: 'ok', on_done=done.append,
                                     name='plain')
    thread.join(timeout=5)
    drain()
    assert done == ['ok']
