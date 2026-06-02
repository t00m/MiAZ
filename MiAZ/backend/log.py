#!/usr/bin/python

"""
# File: log.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: log module
"""

import os
import sys
import datetime
import logging
import logging.handlers
import weakref

# Every MiAZ component creates its own MiAZLog instance, so the loggers are
# independent and do not share handlers through the root logger. To capture a
# complete log file we keep a registry of live instances and a single shared
# file handler that is attached to all of them (existing and future).
_SHARED_FILE_HANDLER = None
_LOGGERS = weakref.WeakSet()

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

class ColorFormatter(logging.Formatter):
    """
    Logging Formatter to add colors and count warning / errors

    via: https://stackoverflow.com/a/56944256/87207
    """

    def format(self, record):
        return FORMATTERS[record.levelno].format(record)


def enable_file_logging(log_file, max_bytes=1048576, backup_count=5):
    """
    Enable persistent file logging for the whole application.

    A single rolling file (`log_file`) is used with rotation. The handler is
    attached to every MiAZLog instance already created and to any created
    afterwards. Returns the path of the active log file.
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

    fmt = '%(asctime)s | %(levelname)8s | %(name)-25s | %(filename)s:%(lineno)d | %(message)s'
    handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8')
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(fmt))
    _SHARED_FILE_HANDLER = handler

    # Retrofit loggers created before file logging was enabled.
    for logger in list(_LOGGERS):
        logger.addHandler(handler)
    return handler.baseFilename


def get_log_file():
    """Return the path of the active log file, or None if not enabled yet."""
    if _SHARED_FILE_HANDLER is not None:
        return _SHARED_FILE_HANDLER.baseFilename
    return None


class MiAZLog(logging.getLoggerClass()):
    """
    C0115: Missing class docstring (missing-class-docstring)
    """

    def __init__(self, name='MiAZ', log_dir=None):
        """
        C0116: Missing function or method docstring (missing-function-docstring)
        """
        super().__init__(name)
        self.file_handler = None

        # Create stream handler for logging to stdout (log all five levels)
        self._stream_handler = logging.StreamHandler(sys.stdout)
        self._stream_handler.setFormatter(ColorFormatter())
        self.enable_console_output()

        # Register instance and attach the shared file handler if persistent
        # logging is already enabled (see enable_file_logging).
        _LOGGERS.add(self)
        if _SHARED_FILE_HANDLER is not None:
            self.addHandler(_SHARED_FILE_HANDLER)


    def add_file_handler(self, name, log_dir):
        """
        Add a file handler for this logger with the specified `name` (and
        store the log file under `log_dir`).
        """
        # Format for file log
        fmt = '%(asctime)s | %(levelname)8s | %(filename)s:%(lineno)d | %(message)s'
        formatter = logging.Formatter(fmt)

        # Determine log path/file name; create log_dir if necessary
        now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        log_name = f'{str(name).replace(" ", "_")}_{now}'
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except Exception:
                print('{}: Cannot create directory {}. '.format(
                    self.__class__.__name__, log_dir),
                    end='', file=sys.stderr)
                log_dir = '/tmp' if sys.platform.startswith('linux') else '.'
                print(f'Defaulting to {log_dir}.', file=sys.stderr)

        log_file = os.path.join(log_dir, log_name) + '.log'

        # Create file handler for logging to a file (log all five levels)
        self.file_handler = logging.FileHandler(log_file)
        self.file_handler.setLevel(logging.DEBUG)
        self.file_handler.setFormatter(formatter)
        self.addHandler(self.file_handler)

    def disable_console_output(self):
        """
        C0116: Missing function or method docstring (missing-function-docstring)
        """
        if not self.has_console_handler():
            return
        self.removeHandler(self._stream_handler)

    def enable_console_output(self):
        """
        C0116: Missing function or method docstring (missing-function-docstring)
        """
        if self.has_console_handler():
            return
        self.addHandler(self._stream_handler)

    def disable_file_output(self):
        """
        C0116: Missing function or method docstring (missing-function-docstring)
        """
        if not self.has_file_handler():
            return
        self.removeHandler(self.file_handler)

    def enable_file_output(self):
        """
        C0116: Missing function or method docstring (missing-function-docstring)
        """
        if self.file_handler is None:
            return
        if self.has_file_handler():
            return
        self.addHandler(self.file_handler)

    def has_console_handler(self):
        """
        C0116: Missing function or method docstring (missing-function-docstring)
        """
        # Strict type identity (not isinstance) intentionally excludes FileHandler,
        # which is a StreamHandler subclass.
        return len([h for h in self.handlers if type(h) is logging.StreamHandler]) > 0

    def has_file_handler(self):
        """
        C0116: Missing function or method docstring (missing-function-docstring)
        """
        return len([h for h in self.handlers if isinstance(h, logging.FileHandler)]) > 0
