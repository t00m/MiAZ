#!/usr/bin/python3

"""The background job queue: what it records and what it serialises.

No display and no GTK: the queue is backend, so the part with the logic worth
testing runs in the headless suite.
"""

import threading
import time

import gi
gi.require_version('GLib', '2.0')

from gi.repository import GLib

from MiAZ.backend import jobs
from MiAZ.backend import tasks
from MiAZ.backend.jobs import MiAZJobQueue


def test_a_job_starts_pending_and_carries_its_name():
    queue = MiAZJobQueue()
    job = queue.add('importdoc-batch')
    assert job.name == 'importdoc-batch'
    assert job.state == 'pending'
    assert job.error is None


def test_a_job_without_a_label_is_named_after_its_slug():
    """The slugs are internal. A call site that matters passes a real label;
    the fallback is deliberately plain, so a developer's words showing up in
    front of a user is the signal that the call site deserves one."""
    queue = MiAZJobQueue()
    assert queue.add('autoscan-scan').label == 'Autoscan scan'


def test_a_label_is_used_as_given():
    queue = MiAZJobQueue()
    assert queue.add('importdoc-batch', label='Importing documents').label == \
        'Importing documents'


def test_an_unqueued_job_starts_at_once():
    """Housekeeping must not wait behind a long import."""
    queue = MiAZJobQueue()
    job = queue.add('workspace-scan')
    queue.start(job)
    assert job.state == 'running'


def test_a_queued_job_waits_for_the_one_holding_the_lane():
    """Two imports copying into one repository at the same time is the thing
    the lane exists to stop."""
    queue = MiAZJobQueue()
    first = queue.add('importdoc-batch', queued=True)
    second = queue.add('importdoc-batch', queued=True)
    queue.start(first)
    queue.start(second)
    assert first.state == 'running'
    assert second.state == 'pending'


def test_finishing_the_lane_holder_starts_the_next_one():
    queue = MiAZJobQueue()
    first = queue.add('importdoc-batch', queued=True)
    second = queue.add('importfromzip', queued=True)
    queue.start(first)
    queue.start(second)
    queue.finish(first)
    assert second.state == 'running'


def test_an_unqueued_job_runs_while_the_lane_is_busy():
    queue = MiAZJobQueue()
    long_job = queue.add('importdoc-batch', queued=True)
    queue.start(long_job)
    scan = queue.add('workspace-scan')
    queue.start(scan)
    assert scan.state == 'running'
    assert long_job.state == 'running'


def test_reporting_records_what_the_worker_said():
    queue = MiAZJobQueue()
    job = queue.add('importdoc-batch')
    queue.start(job)
    queue.report(job, '340 of 1322', 0.257)
    assert job.message == '340 of 1322'
    assert job.fraction == 0.257


def test_a_failed_job_keeps_its_error():
    queue = MiAZJobQueue()
    job = queue.add('importdoc-batch')
    queue.start(job)
    error = OSError('the disk is full')
    queue.finish(job, error)
    assert job.state == 'failed'
    assert job.error is error


def test_running_and_pending_list_what_they_say():
    queue = MiAZJobQueue()
    first = queue.add('importdoc-batch', queued=True)
    second = queue.add('importfromzip', queued=True)
    queue.start(first)
    queue.start(second)
    assert queue.running() == [first]
    assert queue.pending() == [second]


# ---------------------------------------------------------------------------
# The lane, as concurrency rather than as state strings
#
# The state strings passed while the lane serialised nothing: tasks.py started
# the worker thread whether or not the queue had released the job, so a queued
# job read 'pending' in the popover while its work was already copying. These
# tests count how many copies of the work ran at the same time.
# ---------------------------------------------------------------------------

def _probe(seconds: float = 0.05):
    """Work that records how many copies of itself ran at once."""
    state = {'now': 0, 'peak': 0, 'runs': 0}
    lock = threading.Lock()

    def work():
        with lock:
            state['now'] += 1
            state['runs'] += 1
            state['peak'] = max(state['peak'], state['now'])
        time.sleep(seconds)
        with lock:
            state['now'] -= 1

    return state, work


def _drain():
    """Run whatever the queue handed to the main loop, so nothing is left
    armed to fire during another test."""
    context = GLib.MainContext.default()
    while context.pending():
        context.iteration(False)


def test_two_queued_jobs_never_run_their_work_at_the_same_time():
    """The lane's whole purpose: two imports must not copy into the same
    repository at once. Asserted on concurrency, not on job.state, because
    the states read right while both workers were running."""
    queue = MiAZJobQueue()
    tasks.set_job_queue(queue)
    state, work = _probe()
    try:
        first = tasks.run_in_background(work, name='importdoc-batch',
                                        queued=True)
        second = tasks.run_in_background(work, name='importfromzip',
                                         queued=True)
        first.join(timeout=10)
        second.join(timeout=10)
        assert not first.is_alive() and not second.is_alive()
    finally:
        tasks.set_job_queue(None)
        _drain()
    assert state['runs'] == 2, 'both jobs should have run'
    assert state['peak'] == 1, \
        f"{state['peak']} queued jobs ran at once: the lane serialised nothing"


def test_an_unqueued_job_does_not_wait_for_a_held_lane():
    """Housekeeping runs constantly and must never queue behind a five minute
    import."""
    queue = MiAZJobQueue()
    tasks.set_job_queue(queue)
    holding = threading.Event()
    release = threading.Event()
    scanned = threading.Event()

    def holder():
        holding.set()
        release.wait(10)

    try:
        lane = tasks.run_in_background(holder, name='importdoc-batch',
                                       queued=True)
        assert holding.wait(10), 'the lane holder never started'
        scan = tasks.run_in_background(scanned.set, name='workspace-scan')
        assert scanned.wait(5), 'a workspace scan waited behind the lane'
        scan.join(timeout=10)
    finally:
        release.set()
        lane.join(timeout=10)
        tasks.set_job_queue(None)
        _drain()


def test_a_queued_job_runs_after_the_lane_holder_fails():
    """A holder that blows up must hand the lane on, or everything queued
    behind it waits for the rest of the session."""
    queue = MiAZJobQueue()
    tasks.set_job_queue(queue)
    ran = threading.Event()

    def boom():
        raise OSError('the disk is full')

    try:
        first = tasks.run_in_background(boom, on_error=lambda _e: None,
                                        name='importdoc-batch', queued=True)
        second = tasks.run_in_background(ran.set, name='importfromzip',
                                         queued=True)
        assert ran.wait(10), 'the lane was never released by the failed job'
        first.join(timeout=10)
        second.join(timeout=10)
    finally:
        tasks.set_job_queue(None)
        _drain()


def test_a_queued_job_gives_up_waiting_rather_than_parking_forever(monkeypatch):
    """The safety valve. A worker parked for the rest of the session would be
    worse than two copies overlapping, so the wait is bounded, and giving up
    is logged."""
    monkeypatch.setattr(jobs, 'LANE_WAIT_TIMEOUT_S', 0.05)
    queue = MiAZJobQueue()
    holder = queue.add('importdoc-batch', queued=True)
    queue.start(holder)
    waiter = queue.add('importfromzip', queued=True)
    queue.start(waiter)
    assert waiter.state == 'pending'
    assert queue.await_start(waiter) is False, 'the wait should have timed out'
    assert waiter.state == 'running'
    _drain()


def test_an_unqueued_job_never_waits_at_all():
    queue = MiAZJobQueue()
    job = queue.add('workspace-scan')
    started = time.monotonic()
    assert queue.await_start(job) is True
    assert time.monotonic() - started < 0.5
    _drain()


def test_two_queued_jobs_starting_together_cannot_both_take_the_lane():
    """The lane used to be an unguarded check-then-set."""
    for _round in range(50):
        queue = MiAZJobQueue()
        jobs_to_start = [queue.add('importdoc-batch', queued=True),
                         queue.add('importfromzip', queued=True)]
        gate = threading.Barrier(len(jobs_to_start))

        def racer(job):
            gate.wait(5)
            queue.start(job)

        threads = [threading.Thread(target=racer, args=(job,))
                   for job in jobs_to_start]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
        assert len(queue.running()) == 1, 'both jobs took the lane'
    _drain()


def test_a_job_that_already_ended_is_not_started_again():
    """The race this closes: A's finish read B as pending just as B's own
    worker marked it done, and start(B) forced B back to running and pinned
    the lane on a job that had already gone. Every later queued job then
    stayed pending for the rest of the session."""
    queue = MiAZJobQueue()
    holder = queue.add('importdoc-batch', queued=True)
    queue.start(holder)
    queue.finish(holder)
    queue.start(holder)  # the stale wakeup
    assert holder.state == 'done'
    later = queue.add('importfromzip', queued=True)
    queue.start(later)
    assert later.state == 'running', 'the lane was pinned by a finished job'
    _drain()


def test_a_job_removed_while_holding_the_lane_releases_it():
    """The linger timer removes a job from the list. If it still held the lane
    the lane would never come back."""
    queue = MiAZJobQueue()
    holder = queue.add('importdoc-batch', queued=True)
    queue.start(holder)
    waiting = queue.add('importfromzip', queued=True)
    queue.start(waiting)
    queue._forget(holder)
    assert waiting.state == 'running'
    _drain()


# ---------------------------------------------------------------------------
# Failures: listed, marked, and cleared by the next job
# ---------------------------------------------------------------------------

def test_a_failed_job_stays_listed_until_the_next_job_is_added():
    """A spinner that vanishes with no outcome is how a failure goes
    unnoticed. The other half is the leak: every failed job used to keep its
    exception and its traceback for the rest of the session."""
    queue = MiAZJobQueue()
    job = queue.add('importdoc-batch')
    queue.start(job)
    queue.finish(job, OSError('the disk is full'))
    assert queue.failed() == [job]
    assert job in queue.jobs()

    queue.add('workspace-scan')
    assert queue.failed() == []
    assert job not in queue.jobs(), 'the failed job was never cleared'
    _drain()


def test_adding_a_job_keeps_the_running_and_pending_ones():
    """Only the failures go."""
    queue = MiAZJobQueue()
    running = queue.add('importdoc-batch', queued=True)
    queue.start(running)
    waiting = queue.add('importfromzip', queued=True)
    queue.start(waiting)
    broken = queue.add('ocr-process')
    queue.start(broken)
    queue.finish(broken, OSError('nope'))

    queue.add('workspace-scan')
    listed = queue.jobs()
    assert running in listed
    assert waiting in listed
    assert broken not in listed
    _drain()
