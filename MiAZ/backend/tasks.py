#!/usr/bin/python3

"""
# File: tasks.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Run work off the main loop and marshal the result back
"""

import threading

from gi.repository import GLib

from MiAZ.backend.log import MiAZLog

log = MiAZLog('MiAZ.Tasks')


def run_in_background(fn, on_done=None, on_error=None, name=None):
    """Run fn in a daemon thread, then call back on the main loop.

    GTK may only be touched from the main loop, so on_done and on_error are
    delivered through GLib.idle_add rather than called in the worker.

    Without on_error a failure is logged with its traceback. That is the whole
    reason to use this instead of threading.Thread: an exception in a raw worker
    thread dies where nobody sees it unless every caller remembers to wrap its
    own body, and most did not.

    Returns the Thread, so a caller that needs to wait can join it.
    """
    def worker():
        try:
            result = fn()
        except Exception as error:
            if on_error is not None:
                GLib.idle_add(_call_once, on_error, error)
            else:
                log.exception(f"Background task '{thread.name}' failed: {error}")
            return
        if on_done is not None:
            GLib.idle_add(_call_once, on_done, result)

    thread = threading.Thread(target=worker, name=name, daemon=True)
    thread.start()
    return thread


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
