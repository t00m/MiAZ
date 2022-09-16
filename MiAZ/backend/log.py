#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
# File: mod_log.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: log module
"""

import queue
import logging

from MiAZ.backend.env import ENV

levels = {
            10: 'DEBUG',
            20: 'INFO',
            30: 'WARNING',
            40: 'ERROR',
            50: 'CRITICAL'
        }


def get_logger(name):
    """Returns a new logger with personalized.
    @param name: logger name
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)7s | %(lineno)4d  |%(name)-25s | %(asctime)s | %(message)s")
    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(levelname)7s | %(lineno)4d  |%(name)-25s | %(asctime)s | %(message)s")
    fh = logging.FileHandler(ENV['FILE']['LOG'])
    fh.setFormatter(formatter)
    fh.setLevel(logging.DEBUG)
    log.addHandler(fh)

    return log
