#!/usr/bin/python3
# File: crash.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Crash handling helpers (logging + console reporting)

import sys
import datetime
import threading
import traceback

from MiAZ.backend.log import get_log_file

# Where users should report problems.
ISSUE_URL = "https://github.com/t00m/MiAZ/issues"


def format_summary(exc_type, exc_value):
    """Return a short one-line description of the exception."""
    name = getattr(exc_type, '__name__', str(exc_type))
    return f"{name}: {exc_value}"


def format_report(env, exc_type, exc_value, exc_tb):
    """Build a full crash report: environment info plus the Python traceback."""
    lines = []
    try:
        app = env.get('APP', {}) if env else {}
        lines.append(f"{app.get('shortname', 'MiAZ')} v{app.get('VERSION', '')}")
    except Exception:
        pass
    try:
        desktop = env.get('DESKTOP', {}) if env else {}
        lines.append(f"GTK: {desktop.get('GTK_VERSION')}  "
                     f"Adw: {desktop.get('ADW_VERSION')}")
    except Exception:
        pass
    lines.append(f"Python: {sys.version.split()[0]}  Platform: {sys.platform}")
    lines.append(f"Timestamp: {datetime.datetime.now().isoformat(timespec='seconds')}")
    lines.append("")
    lines.append("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
    return "\n".join(lines)


def _print_console(summary, log_file):
    """Print a console message pointing to the log file and the issue tracker."""
    sep = "=" * 60
    msg = [sep, "MiAZ has encountered an unexpected error.", f"Error: {summary}"]
    if log_file:
        msg.append("A detailed log was saved to:")
        msg.append(f"  {log_file}")
    msg.append("Please report this issue at:")
    msg.append(f"  {ISSUE_URL}")
    msg.append(sep)
    print("\n".join(msg), file=sys.stderr)


def handle_exception(logger, env, exc_type, exc_value, exc_tb, log_file=None):
    """
    Log a crash report and print a console pointer.

    Returns the report text, or None when the exception is a KeyboardInterrupt
    (which is delegated to the default handler so Ctrl-C keeps working).
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return None

    report = format_report(env, exc_type, exc_value, exc_tb)
    summary = format_summary(exc_type, exc_value)
    try:
        logger.critical(f"Unhandled exception: {summary}")
        logger.critical("Crash report:\n%s", report)
    except Exception:
        pass
    _print_console(summary, log_file or get_log_file())
    return report


def install_backend_excepthook(logger, env):
    """
    Install a console/log-only excepthook for the main thread and worker
    threads. The desktop frontend replaces this later with a variant that also
    shows a dialog; this guarantees crashes are logged even without a GUI.
    """
    def _hook(exc_type, exc_value, exc_tb):
        handle_exception(logger, env, exc_type, exc_value, exc_tb)
    sys.excepthook = _hook

    def _thread_hook(args):
        if issubclass(args.exc_type, SystemExit):
            return
        handle_exception(logger, env, args.exc_type, args.exc_value,
                         args.exc_traceback)
    threading.excepthook = _thread_hook
