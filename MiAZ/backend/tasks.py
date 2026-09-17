
"""
# File: tasks.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Run work off the main loop and marshal the result back
"""

import inspect
import threading

from gi.repository import GLib

from MiAZ.backend.log import MiAZLog

log = MiAZLog('MiAZ.Tasks')

# The job queue, when there is one. The desktop application installs it at
# startup; the console frontend does not, and gets the behaviour this module
# had before there was a queue at all.
#
# It lives here rather than in jobs.py so that the dependency runs one way:
# jobs.py imports run_on_main from this module, and this module never imports
# jobs.py. It holds the instance and calls methods on it.
_JOB_QUEUE = None


def set_job_queue(queue):
    """Install the queue every background job registers with, or None."""
    global _JOB_QUEUE
    _JOB_QUEUE = queue


def job_queue():
    """The installed queue, or None when nothing is watching."""
    return _JOB_QUEUE


def run_in_background(fn, on_done=None, on_error=None, name=None,
                      label=None, queued=False):
    """Run fn in a daemon thread, then call back on the main loop.

    GTK may only be touched from the main loop, so on_done and on_error are
    delivered through GLib.idle_add rather than called in the worker.

    Without on_error a failure is logged with its traceback. That is the whole
    reason to use this instead of threading.Thread: an exception in a raw worker
    thread dies where nobody sees it unless every caller remembers to wrap its
    own body, and most did not.

    When a queue is installed the work registers as a job, which is what puts
    it in the headerbar indicator. `label` is what the user reads, falling back
    to `name`. `queued` asks for the lane: the job waits until no other queued
    job is running, which is how two imports are kept off the same repository.

    A fn that takes a `report` parameter is given one, bound to its job, with
    the same (message, fraction) signature MiAZProgress uses. A fn that does
    not is called with no arguments, which is all twenty existing callers.

    Returns the Thread, so a caller that needs to wait can join it.
    """
    queue = job_queue()
    job = None
    if queue is not None:
        try:
            job = queue.add(name or 'work', label=label, queued=queued)
        except Exception as error:
            # A broken indicator must never stop the work it is watching.
            log.warning(f"Could not register job '{name}': {error}")

    wants_report = _accepts_report(fn)

    def report(message, fraction=None):
        if queue is not None and job is not None:
            try:
                queue.report(job, message, fraction)
            except Exception as error:
                log.warning(f"Could not report progress for '{name}': {error}")

    def worker():
        failure = None
        try:
            result = fn(report=report) if wants_report else fn()
            if on_done is not None:
                GLib.idle_add(_call_once, on_done, result)
        except Exception as error:
            failure = error
            if on_error is not None:
                GLib.idle_add(_call_once, on_error, error)
            else:
                log.exception(f"Background task '{thread.name}' failed: {error}")
        finally:
            # In the finally, not the success path: a job whose worker died
            # without finishing would hold the lane for the rest of the
            # session.
            if queue is not None and job is not None:
                try:
                    queue.finish(job, failure)
                except Exception as error:
                    log.warning(f"Could not finish job '{name}': {error}")

    try:
        thread = threading.Thread(target=worker, name=name, daemon=True)
        if queue is not None and job is not None:
            try:
                queue.start(job)
            except Exception as error:
                log.warning(f"Could not start job '{name}': {error}")
        thread.start()
    except Exception as error:
        # thread.start() can fail after queue.start(job) already succeeded.
        # worker() never ran, so its own finally never ran either: without
        # this, the job would stay registered and running for the rest of
        # the session, holding the lane forever if queued=True.
        if queue is not None and job is not None:
            try:
                queue.finish(job, error)
            except Exception as finish_error:
                log.warning(f"Could not finish job '{name}': {finish_error}")
        raise
    return thread


def _accepts_report(fn) -> bool:
    """Whether fn wants a progress reporter passed to it.

    Asked once, before the thread starts, so a signature that cannot be read
    (a builtin, a C function) simply means no reporter rather than a failure.
    """
    try:
        return 'report' in inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return False


def run_on_main(callback, *args, **kwargs):
    """Run the callback once on the main loop, whatever it returns.

    Use this instead of GLib.idle_add for anything whose return value is not
    yours to control. GLib repeats an idle source until the callback returns
    something falsy, so idle_add(srvdlg.show_toast, msg) never lets go:
    show_toast returns the Adw.Toast it created, and the toast is built again
    on every iteration of the main loop.

    An exception in the callback is logged and does not leave the source armed
    either. Returns nothing: there is no source left to remove.
    """
    def once():
        try:
            callback(*args, **kwargs)
        except Exception as error:
            log.exception(f"Main loop callback failed: {error}")
        return False

    GLib.idle_add(once)


def _call_once(callback, value):
    """Run the callback on the main loop and never repeat it.

    GLib repeats an idle source until it returns False, so returning False here
    is what removes it.
    """
    try:
        callback(value)
    except Exception as error:
        log.exception(f"Background task callback failed: {error}")
    return False
