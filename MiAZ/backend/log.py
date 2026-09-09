
"""
# File: log.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: log module
"""

import os
import shutil
import sys
import logging
import logging.handlers

# Every MiAZ logger hangs off one root, 'MiAZ', and only that root carries
# handlers: one for the console, one for the file when persistent logging is
# on. Children propagate up to it, so the whole application logs through two
# handlers rather than two per component.
#
# The root does not propagate any further. Whatever an embedding application
# has configured on the Python root logger, MiAZ diagnostics are not duplicated
# into it.
ROOT = 'MiAZ'

def debug_requested() -> bool:
    """Whether MIAZ_DEBUG asks for the startup narration on screen.

    One definition of the rule. It was read in four places, three of them
    silencing the console before a command runs, and a fifth written slightly
    differently would have been an easy mistake to make.
    """
    return bool(os.environ.get('MIAZ_DEBUG'))


# What the console shows unless something says otherwise. DEBUG is written to
# the log file and kept out of the terminal, where it buries the lines a user
# can act on. MIAZ_DEBUG=1 puts it back on screen.
DEFAULT_CONSOLE_LEVEL = logging.DEBUG if debug_requested() else logging.INFO

_SHARED_FILE_HANDLER = None

# Define colors
GREY = "\x1b[38;20m"
CYAN = "\x1b[36;20m"
MAUVE = "\x1b[34;20m"
YELLOW = "\x1b[33;20m"
RED = "\x1b[31;20m"
BOLD_RED = "\x1b[31;1m"
RESET = "\x1b[0m"


def make_format(color):
    return f"{color}%(levelname)7s | %(lineno)4d  |%(name)-25s | %(asctime)s | %(message)s{RESET}"

FORMATS = {
    logging.DEBUG: make_format(GREY),
    logging.INFO: make_format(CYAN),
    logging.WARNING: make_format(YELLOW),
    logging.ERROR: make_format(RED),
    logging.CRITICAL: make_format(BOLD_RED),
}

FORMATTERS = {level: logging.Formatter(FORMATS[level]) for level in FORMATS.keys()}

# Same layout without the escape codes, for anything that is not a terminal.
PLAIN_FORMATTER = logging.Formatter(
    "%(levelname)7s | %(lineno)4d  |%(name)-25s | %(asctime)s | %(message)s")


def supports_color(stream):
    """True when writing colour to this stream makes sense.

    Redirected output keeps the escape codes otherwise, which is noise in a
    file and breaks anything reading the diagnostics. NO_COLOR is the de facto
    way for a user to say they never want them (https://no-color.org).
    """
    if os.environ.get('NO_COLOR'):
        return False
    try:
        return bool(stream.isatty())
    except Exception:
        # A stream without isatty is not a terminal as far as we care.
        return False


class ColorFormatter(logging.Formatter):
    """Colour on a terminal, plain text anywhere else.

    via: https://stackoverflow.com/a/56944256/87207
    """

    def __init__(self, color=True):
        super().__init__()
        self.color = color

    def format(self, record):
        if not self.color:
            return PLAIN_FORMATTER.format(record)
        # An unknown level (a plugin calling log.log(25, ...)) must not cost
        # the message: logging catches the KeyError, drops the line and prints
        # its own error instead. Fall back to the INFO colour.
        formatter = FORMATTERS.get(record.levelno, FORMATTERS[logging.INFO])
        return formatter.format(record)


def _build_root():
    """Configure the 'MiAZ' logger once, on import.

    Diagnostics go to stderr, never stdout: the command line writes results to
    stdout, and log lines mixed into them would break every pipe.
    """
    root = logging.getLogger(ROOT)
    # The root passes everything through; each handler decides its own floor,
    # so the file can keep DEBUG while the console starts at INFO.
    root.setLevel(logging.DEBUG)
    root.propagate = False
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(DEFAULT_CONSOLE_LEVEL)
    handler.setFormatter(ColorFormatter(color=supports_color(sys.stderr)))
    root.addHandler(handler)
    return root, handler


_ROOT_LOGGER, _CONSOLE_HANDLER = _build_root()


def _hierarchical(name):
    """Put a logger name under the MiAZ root.

    Names arrive in three shapes and all three end up in one tree:

        MiAZ.Index           already there, untouched
        MiAZPlugin           MiAZ.Plugin
        Plugin.MiAZInsights  MiAZ.Plugin.MiAZInsights
    """
    if name == ROOT or name.startswith(f'{ROOT}.'):
        return name
    if name.startswith(ROOT):
        return f'{ROOT}.{name[len(ROOT):]}'
    return f'{ROOT}.{name}'


def MiAZLog(name=ROOT, log_dir=None):  # noqa: N802 (kept for its 66 call sites)
    """Return the logger for `name`.

    A factory, not a class, though the name says otherwise. It used to build a
    Logger subclass directly, which kept every logger out of the logging
    hierarchy and gave each one its own handler: a name asked for twice
    produced two loggers, and 'MiAZ.Workspace' had no relationship to 'MiAZ'.
    Going through getLogger means the manager caches by name, parents resolve,
    and setLevel on a parent controls its whole subtree.
    """
    return logging.getLogger(_hierarchical(name))


def set_console_level(level):
    """Set what reaches the console, for the whole application.

    The command line uses it to keep the DEBUG chatter out of the way: a
    program that prints filenames should not also narrate its startup. The file
    handler is unaffected, so the log file keeps everything.
    """
    _CONSOLE_HANDLER.setLevel(level)


def previous_log_file(log_file):
    """Where the run before this one is kept: MiAZ.log -> MiAZ.last.log."""
    stem, extension = os.path.splitext(log_file)
    return f'{stem}.last{extension or ".log"}'


def _keep_previous_run(log_file):
    """Move the last run aside and leave an empty file for this one.

    One run back, not a rotation history: when something goes wrong the file
    you want is almost always the run that just failed, and the one before it
    for comparison.

    The truncation is done here rather than by opening the handler with
    mode='w', because RotatingFileHandler ignores that and forces append
    whenever rotation is enabled, which it is.
    """
    if not os.path.exists(log_file):
        return
    try:
        shutil.copy2(log_file, previous_log_file(log_file))
        with open(log_file, 'w', encoding='utf-8'):
            pass
    except OSError as error:
        print(f'MiAZLog: cannot keep the previous log: {error}', file=sys.stderr)


def enable_file_logging(log_file, max_bytes=1048576, backup_count=5):
    """
    Enable persistent file logging for the whole application.

    A single rolling file (`log_file`) is used with rotation. The handler goes
    on the root logger, so every MiAZ logger reaches it by propagation, whether
    it was created before this call or after. Returns the path of the active
    log file.
    """
    global _SHARED_FILE_HANDLER
    if _SHARED_FILE_HANDLER is not None:
        return _SHARED_FILE_HANDLER.baseFilename

    log_dir = os.path.dirname(log_file)
    try:
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
    except Exception:
        log_dir = '/tmp' if sys.platform.startswith('linux') else '.'
        log_file = os.path.join(log_dir, os.path.basename(log_file))
        print(f"MiAZLog: cannot create log directory, defaulting to {log_dir}",
              file=sys.stderr)

    _keep_previous_run(log_file)

    fmt = '%(asctime)s | %(levelname)8s | %(name)-25s | %(filename)s:%(lineno)d | %(message)s'
    # The file is already empty (see _keep_previous_run); rotation caps a single
    # runaway run on top of that.
    handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8')
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(fmt))
    _SHARED_FILE_HANDLER = handler
    _ROOT_LOGGER.addHandler(handler)
    return handler.baseFilename


def get_log_file():
    """Return the path of the active log file, or None if not enabled yet."""
    if _SHARED_FILE_HANDLER is not None:
        return _SHARED_FILE_HANDLER.baseFilename
    return None
