#!/usr/bin/python3

"""
# File: status.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: MiAZ Status during execution
"""

from enum import IntEnum


class MiAZStatus(IntEnum):
    RUNNING = 0     # Normal operation
    BUSY = 1        # No update allowed (eg.: switching repos)
