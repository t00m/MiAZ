#!/usr/bin/python3

"""
# File: gate.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Reference-counted suspension of an expensive refresh
"""


class UpdateGate:
    """Holds back an update while something is working, and runs it once after.

    Replaces a plain "busy" flag. A flag cannot say how many operations are in
    flight, so two overlapping ones ended with the first to finish clearing it
    while the second was still going, and anything raising in between left it set
    for good. This counts holders and releases through a handle, so both cases
    come out right.

        with workspace.suspend_updates():
            for path in files:
                util.filename_import(path, target)

    Work that spans a thread keeps the handle instead:

        handle = workspace.suspend_updates()
        ...
        GLib.idle_add(handle.release)
    """

    def __init__(self, on_release):
        self._on_release = on_release
        self._depth = 0
        self._wanted = False

    def suspend(self):
        """Suspend updates now.

        Returns a handle: use it as a context manager, or call release() on it
        when the work finishes somewhere else.
        """
        self._depth += 1
        return SuspendHandle(self)

    def is_suspended(self) -> bool:
        return self._depth > 0

    def request(self) -> bool:
        """True when the caller should update now.

        While suspended it records that an update is due and returns False; the
        update runs once when the last holder releases, however many times it
        was asked for meanwhile.
        """
        if self._depth > 0:
            self._wanted = True
            return False
        return True

    def _release(self):
        if self._depth == 0:
            return
        self._depth -= 1
        if self._depth > 0 or not self._wanted:
            return
        self._wanted = False
        # Depth is already back to zero, so a callback that raises propagates
        # without leaving the gate shut.
        self._on_release()


class SuspendHandle:
    """One holder of an UpdateGate. Releasing twice does nothing the second time."""

    def __init__(self, gate):
        self._gate = gate
        self._released = False

    def release(self) -> bool:
        """Give up this hold. Returns False when it was already given up."""
        if self._released:
            return False
        self._released = True
        self._gate._release()
        return True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()
        return False
