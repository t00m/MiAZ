#!/usr/bin/python3

"""The background job queue: what it records and what it serialises.

No display and no GTK: the queue is backend, so the part with the logic worth
testing runs in the headless suite.
"""

import gi
gi.require_version('GLib', '2.0')

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
