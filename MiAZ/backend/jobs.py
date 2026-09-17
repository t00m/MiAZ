# File: jobs.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: What is running in the background, and what is waiting

import threading

from gi.repository import GLib
from gi.repository import GObject

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.tasks import run_on_main

# How long a finished job stays listed. Long enough to be seen finishing, short
# enough that the indicator empties on its own.
DONE_LINGER_MS = 3000

# The longest a queued job waits for the lane before running anyway. The lane
# is released from a finally in the worker, so the only way to reach this is a
# holder that never returned at all: a copy stuck on a dead network mount, for
# instance. A worker parked for the rest of the session is worse than two
# copies overlapping, so the wait gives up, says so in the log, and runs.
LANE_WAIT_TIMEOUT_S = 1800

PENDING = 'pending'
RUNNING = 'running'
DONE = 'done'
FAILED = 'failed'


class MiAZJob:
    """One piece of background work, and what is known about it."""

    def __init__(self, name: str, label: str = None, queued: bool = False):
        self.name = name
        self.label = label or self._label_from(name)
        self.queued = queued
        self.state = PENDING
        self.message = ''
        self.fraction = None
        self.error = None
        # What the worker waits on. The queue sets it when the job may run, so
        # the queue is what decides when a queued job begins rather than the
        # thread starting whenever it was created.
        self.gate = threading.Event()

    @staticmethod
    def _label_from(name: str) -> str:
        """A readable fallback for a call site that passed no label.

        Deliberately plain. It is a developer's slug shown to a user, which is
        the signal that the call site deserves a label of its own.
        """
        return name.replace('-', ' ').capitalize() if name else 'Working'

    def __repr__(self):
        return f"<MiAZJob {self.name} {self.state}>"


class MiAZJobQueue(GObject.GObject):
    """Every background job, and one lane for the long ones.

    The lane is what stops two imports copying into the same repository at
    once. Everything else starts the moment it is asked to, because the
    housekeeping that makes up most of the jobs here runs constantly and must
    not queue behind a five minute import.

    One lock covers every mutation. The workers add, start, report and finish
    jobs from their own threads while the main loop reads the list and forgets
    finished jobs, so the lane's check-then-set and the handover in `finish`
    both have to be atomic. Signals are emitted after the lock is released,
    through `run_on_main`, so a GTK widget only ever sees consistent state
    from the thread it is allowed to run on.
    """
    __gtype_name__ = 'MiAZJobQueue'

    __gsignals__ = {
        'job-added': (GObject.SignalFlags.RUN_LAST, None, (object,)),
        'job-changed': (GObject.SignalFlags.RUN_LAST, None, (object,)),
        'job-removed': (GObject.SignalFlags.RUN_LAST, None, (object,)),
    }

    def __init__(self):
        super().__init__()
        self.log = MiAZLog('MiAZ.Jobs')
        self._jobs = []
        self._lane = None
        self._mutex = threading.Lock()

    def add(self, name: str, label: str = None, queued: bool = False) -> MiAZJob:
        job = MiAZJob(name, label=label, queued=queued)
        with self._mutex:
            # A failure stays listed until the next job is added, and then it
            # goes. Nothing used to clear them, so every failed job kept its
            # exception and its traceback frames for the rest of the session.
            cleared = [old for old in self._jobs if old.state == FAILED]
            for old in cleared:
                self._jobs.remove(old)
            self._jobs.append(job)
        for old in cleared:
            run_on_main(self.emit, 'job-removed', old)
        run_on_main(self.emit, 'job-added', job)
        return job

    def start(self, job: MiAZJob):
        """Run it now, or leave it waiting for the lane."""
        with self._mutex:
            started = self._start_locked(job)
        if started:
            run_on_main(self.emit, 'job-changed', job)

    def await_start(self, job: MiAZJob, timeout=None) -> bool:
        """Block the caller until this job may do its work.

        This is what makes the lane a lane. `start` alone only recorded the
        decision; the worker thread ran regardless, so two imports could copy
        into the same repository while one of them still read as pending.

        An unqueued job never waits, not even for an instant: a workspace scan
        must not queue behind a five minute import.

        Returns whether the queue released the job. False means the wait timed
        out and the job runs anyway, which is logged.
        """
        if not job.queued:
            return True
        if timeout is None:
            timeout = LANE_WAIT_TIMEOUT_S
        if job.gate.wait(timeout):
            return True
        self.log.warning(
            f"Job '{job.name}' waited {timeout}s for the lane and is running"
            " anyway: whatever held the lane never finished")
        with self._mutex:
            self._lane = job
            job.state = RUNNING
            job.gate.set()
        run_on_main(self.emit, 'job-changed', job)
        return False

    def report(self, job: MiAZJob, message: str, fraction=None):
        with self._mutex:
            job.message = message
            job.fraction = fraction
        run_on_main(self.emit, 'job-changed', job)

    def finish(self, job: MiAZJob, error: Exception = None):
        with self._mutex:
            job.state = FAILED if error is not None else DONE
            job.error = error
            # A job that ended is waiting for nothing. Without this a job
            # finished while still pending, which is what happens when its
            # thread could not start, would leave its worker parked if one
            # ever did appear.
            job.gate.set()
            if self._lane is job:
                self._lane = None
            following = self._next_locked()
        run_on_main(self.emit, 'job-changed', job)
        if following is not None:
            run_on_main(self.emit, 'job-changed', following)
        if error is None:
            GLib.timeout_add(DONE_LINGER_MS, self._forget, job)

    def _start_locked(self, job: MiAZJob):
        """Let the job run, if it may. The caller holds the mutex.

        A job that is not pending is left alone. That is the guard against a
        stale wakeup: a `finish` that read a job as pending just as the job's
        own worker marked it done used to force it back to running and pin the
        lane on a job that had already gone, leaving every later queued job
        pending for the rest of the session.
        """
        if job.state != PENDING:
            return False
        if job.queued:
            if self._lane is not None:
                return False
            self._lane = job
        job.state = RUNNING
        job.gate.set()
        return True

    def _next_locked(self):
        """Let the oldest waiting queued job run. The caller holds the mutex.

        Returns the job it released, so the caller can emit for it once the
        lock is gone.
        """
        for job in self._jobs:
            if job.queued and job.state == PENDING:
                return job if self._start_locked(job) else None
        return None

    def _forget(self, job: MiAZJob):
        with self._mutex:
            listed = job in self._jobs
            if listed:
                self._jobs.remove(job)
            following = None
            if self._lane is job:
                # Belt and braces. A job dropped from the list while it still
                # held the lane would hold it for the rest of the session.
                self._lane = None
                following = self._next_locked()
        if listed:
            run_on_main(self.emit, 'job-removed', job)
        if following is not None:
            run_on_main(self.emit, 'job-changed', following)
        return GLib.SOURCE_REMOVE

    def jobs(self) -> list:
        with self._mutex:
            return list(self._jobs)

    def running(self) -> list:
        with self._mutex:
            return [job for job in self._jobs if job.state == RUNNING]

    def pending(self) -> list:
        with self._mutex:
            return [job for job in self._jobs if job.state == PENDING]

    def failed(self) -> list:
        """The failures still listed, for the indicator to show.

        A spinner that vanishes with no outcome is how a failure goes
        unnoticed, so these keep the indicator on screen until the next job
        is added.
        """
        with self._mutex:
            return [job for job in self._jobs if job.state == FAILED]
