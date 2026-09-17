# File: jobs.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: What is running in the background, and what is waiting

from gi.repository import GLib
from gi.repository import GObject

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.tasks import run_on_main

# How long a finished job stays listed. Long enough to be seen finishing, short
# enough that the indicator empties on its own.
DONE_LINGER_MS = 3000

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

    Nothing mutates a job except on the main loop: the workers create and
    finish them, and a GTK widget is reading them.
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

    def add(self, name: str, label: str = None, queued: bool = False) -> MiAZJob:
        job = MiAZJob(name, label=label, queued=queued)
        self._jobs.append(job)
        run_on_main(self.emit, 'job-added', job)
        return job

    def start(self, job: MiAZJob):
        """Run it now, or leave it waiting for the lane."""
        if job.queued and self._lane is not None and self._lane is not job:
            return
        if job.queued:
            self._lane = job
        job.state = RUNNING
        run_on_main(self.emit, 'job-changed', job)

    def report(self, job: MiAZJob, message: str, fraction=None):
        job.message = message
        job.fraction = fraction
        run_on_main(self.emit, 'job-changed', job)

    def finish(self, job: MiAZJob, error: Exception = None):
        job.state = FAILED if error is not None else DONE
        job.error = error
        if self._lane is job:
            self._lane = None
        run_on_main(self.emit, 'job-changed', job)
        if error is None:
            GLib.timeout_add(DONE_LINGER_MS, self._forget, job)
        self._start_next()

    def _start_next(self):
        for job in self._jobs:
            if job.queued and job.state == PENDING:
                self.start(job)
                return

    def _forget(self, job: MiAZJob):
        if job in self._jobs:
            self._jobs.remove(job)
            run_on_main(self.emit, 'job-removed', job)
        return GLib.SOURCE_REMOVE

    def jobs(self) -> list:
        return list(self._jobs)

    def running(self) -> list:
        return [job for job in self._jobs if job.state == RUNNING]

    def pending(self) -> list:
        return [job for job in self._jobs if job.state == PENDING]
