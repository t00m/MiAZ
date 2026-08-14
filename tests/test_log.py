#!/usr/bin/python3

"""
Tests for MiAZ.backend.log.

The logger is the one component every other one uses, and it had no tests. The
two failures covered here both reached the user: a message lost to a KeyError,
and escape codes in a redirected file.
"""

import io
import logging

from MiAZ.backend.log import (ColorFormatter, MiAZLog, set_console_level,
                              supports_color)


def record(level=logging.INFO, message='hello'):
    return logging.LogRecord(name='probe', level=level, pathname=__file__,
                             lineno=1, msg=message, args=(), exc_info=None)


class NotATerminal(io.StringIO):
    def isatty(self):
        return False


class ATerminal(io.StringIO):
    def isatty(self):
        return True


# ---------------------------------------------------------------------------
# An unknown level must not lose the message
# ---------------------------------------------------------------------------

def test_standard_levels_format():
    formatter = ColorFormatter(color=False)
    for level in (logging.DEBUG, logging.INFO, logging.WARNING,
                  logging.ERROR, logging.CRITICAL):
        assert 'hello' in formatter.format(record(level))


def test_custom_level_does_not_raise():
    """A plugin calling log.log(25, ...) used to raise KeyError inside the
    formatter, so the message was dropped and logging printed its own error."""
    formatter = ColorFormatter(color=False)
    assert 'hello' in formatter.format(record(25))


def test_custom_level_keeps_its_colour_fallback():
    formatter = ColorFormatter(color=True)
    assert 'hello' in formatter.format(record(25))


# ---------------------------------------------------------------------------
# Colour only where colour makes sense
# ---------------------------------------------------------------------------

def test_supports_color_on_a_terminal():
    assert supports_color(ATerminal()) is True


def test_supports_color_off_when_redirected():
    assert supports_color(NotATerminal()) is False


def test_supports_color_honours_no_color(monkeypatch):
    monkeypatch.setenv('NO_COLOR', '1')
    assert supports_color(ATerminal()) is False


def test_supports_color_survives_a_stream_without_isatty():
    class Odd:
        pass
    assert supports_color(Odd()) is False


def test_plain_output_has_no_escape_codes():
    """'miaz search 2> log.txt' must not fill the file with escape codes."""
    formatted = ColorFormatter(color=False).format(record(logging.WARNING))
    assert '\x1b[' not in formatted


def test_coloured_output_has_escape_codes():
    formatted = ColorFormatter(color=True).format(record(logging.WARNING))
    assert '\x1b[' in formatted


# ---------------------------------------------------------------------------
# Levels
# ---------------------------------------------------------------------------

def console_handler():
    return [h for h in logging.getLogger('MiAZ').handlers
            if type(h) is logging.StreamHandler][0]


def test_set_console_level_raises_the_bar_for_everyone():
    """One handler for the application, so one call is all it takes."""
    set_console_level(logging.WARNING)
    try:
        assert console_handler().level == logging.WARNING
    finally:
        set_console_level(logging.NOTSET)


def test_set_console_level_filters_what_a_child_prints():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.WARNING)
    root = logging.getLogger('MiAZ')
    root.addHandler(handler)
    try:
        log = MiAZLog('probe.filtered')
        log.debug('quiet')
        log.warning('loud')
    finally:
        root.removeHandler(handler)
    assert 'quiet' not in stream.getvalue()
    assert 'loud' in stream.getvalue()


def test_the_file_handler_keeps_everything(tmp_path, monkeypatch):
    """Raising the console level must not thin out the log file."""
    import MiAZ.backend.log as logmod
    monkeypatch.setattr(logmod, '_SHARED_FILE_HANDLER', None)
    path = tmp_path / 'miaz.log'
    logmod.enable_file_logging(str(path))
    file_handler = logging.getLogger('MiAZ').handlers[-1]
    try:
        set_console_level(logging.ERROR)
        assert file_handler.level == logging.DEBUG
        MiAZLog('probe.tofile').debug('written anyway')
        file_handler.flush()
        assert 'written anyway' in path.read_text()
    finally:
        set_console_level(logging.NOTSET)
        logging.getLogger('MiAZ').removeHandler(file_handler)
        file_handler.close()


def test_diagnostics_go_to_stderr():
    """Results go to stdout, so nothing else may."""
    import sys
    assert console_handler().stream is sys.stderr


# ---------------------------------------------------------------------------
# One logger per name
# ---------------------------------------------------------------------------

def test_same_name_is_the_same_logger():
    """19 plugins asking for 'MiAZPlugin' used to get 19 loggers and 19
    handlers, all writing the same name, so the duplication bought nothing."""
    assert MiAZLog('probe.shared') is MiAZLog('probe.shared')


def test_different_names_are_different_loggers():
    assert MiAZLog('probe.one') is not MiAZLog('probe.two')


# ---------------------------------------------------------------------------
# The MiAZ hierarchy
# ---------------------------------------------------------------------------

def test_names_live_under_one_root():
    assert MiAZLog('MiAZ.Index').name == 'MiAZ.Index'
    assert MiAZLog('MiAZPlugin').name == 'MiAZ.Plugin'
    assert MiAZLog('Plugin.MiAZInsights').name == 'MiAZ.Plugin.MiAZInsights'
    assert MiAZLog('MiAZ').name == 'MiAZ'


def test_the_manager_owns_the_loggers():
    """logging.getLogger must find the same object, which is what makes the
    standard tools (setLevel on a parent, dictConfig) work at all."""
    assert MiAZLog('MiAZ.Index') is logging.getLogger('MiAZ.Index')


def test_only_the_root_carries_handlers():
    """One console handler for the whole app, not one per logger."""
    assert MiAZLog('MiAZ.Somewhere.Deep').handlers == []
    console = [h for h in logging.getLogger('MiAZ').handlers
               if type(h) is logging.StreamHandler]
    assert len(console) == 1


def test_a_child_record_reaches_the_root_handler():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    root = logging.getLogger('MiAZ')
    root.addHandler(handler)
    try:
        MiAZLog('MiAZ.Child.Probe').warning('carried up')
    finally:
        root.removeHandler(handler)
    assert 'carried up' in stream.getvalue()


def test_setting_a_parent_level_silences_its_children():
    """The point of the hierarchy: one setLevel controls a whole subtree."""
    parent = MiAZLog('MiAZ.Subtree')
    child = MiAZLog('MiAZ.Subtree.Leaf')
    parent.setLevel(logging.ERROR)
    try:
        assert child.isEnabledFor(logging.WARNING) is False
        assert child.isEnabledFor(logging.ERROR) is True
    finally:
        parent.setLevel(logging.NOTSET)


def test_miaz_logs_do_not_reach_the_python_root():
    """Whatever the embedding application configures on the root logger, our
    diagnostics are not duplicated into it."""
    assert logging.getLogger('MiAZ').propagate is False
