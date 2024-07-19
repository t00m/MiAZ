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
from enum import Enum

TRACE = logging.DEBUG - 1
setattr(logging, "TRACE", TRACE)
logging.addLevelName(TRACE, "TRACE")


class DebugLevel(int, Enum):
    NONE = 0
    DEFAULT = 1
    TRACE = 2
    SUPERTRACE = 3


GREY = "\x1b[38;21m"
CYAN = "\x1b[36;21m"
MAUVE = "\x1b[34;21m"
YELLOW = "\x1b[33;21m"
RED = "\x1b[31;21m"
BOLD_RED = "\x1b[31;1m"
RESET = "\x1b[0m"


def make_format(color):
    return f"{color}%(levelname)s{RESET}: %(name)s: %(message)s"


FORMATS = {
    logging.TRACE: make_format(MAUVE),  # type: ignore
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


class LoggerWithTrace(logging.getLoggerClass()):  # type: ignore
    def trace(self, msg, *args, **kwargs):
        self.log(TRACE, msg, *args, **kwargs)


logging.setLoggerClass(LoggerWithTrace)

def get_logger(name) -> LoggerWithTrace:
    """
    a logging constructor that guarantees that the TRACE level is available.
    use this just like `logging.getLogger`.

    because we patch stdlib logging upon import of this module (side-effect),
    and we can't be sure how callers order their imports,
    then we want to provide a way to ensure that callers can access TRACE consistently.
    if callers use `floss.logging.getLogger()` intead of `logging.getLogger()`,
    then they'll be guaranteed to have access to TRACE.
    """
    logger = logging.getLogger(name)  # type: ignore
    # ~ logger.propagate = False
    return logger


class MiAZLog(logging.getLoggerClass()):
    """
    C0115: Missing class docstring (missing-class-docstring)
    """
    counter = 0
    logger_initialized = False
    stdout_handler = None

    def __init__(self, name='MiAZ', log_dir=None):
        """
        C0116: Missing function or method docstring (missing-function-docstring)
        """
        super().__init__(name)
        # ~ print(dir(self.root))
        # ~ exit()

        # Create custom logger logging all five levels
        self.setLevel(logging.DEBUG)

        # Create stream handler for logging to stdout (log all five levels)
        if self.stdout_handler is None:
            self.stdout_handler = logging.StreamHandler(sys.stdout)
            self.stdout_handler.setLevel(logging.DEBUG)
            self.stdout_handler.setFormatter(logging.Formatter("%(levelname)7s | %(lineno)4d  |%(name)-25s | %(asctime)s | %(message)s"))
            self.enable_console_output()

        # Add file handler only if the log directory was specified
        # ~ self.file_handler = None
        # ~ if log_dir:
            # ~ self.add_file_handler(name, log_dir)

        self.logger_initialized = True


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
        self.removeHandler(self.stdout_handler)

    def enable_console_output(self):
        """
        C0116: Missing function or method docstring (missing-function-docstring)
        """
        if self.has_console_handler():
            return
        self.addHandler(self.stdout_handler)

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
        if self.has_file_handler():
            return
        self.addHandler(self.file_handler)

    def has_console_handler(self):
        """
        C0116: Missing function or method docstring (missing-function-docstring)
        """
        return len([h for h in self.handlers if type(h) == logging.StreamHandler]) > 0

    def has_file_handler(self):
        """
        C0116: Missing function or method docstring (missing-function-docstring)
        """
        return len([h for h in self.handlers if isinstance(h, logging.FileHandler)]) > 0
