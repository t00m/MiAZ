#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: widget.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Not used
"""

import logging
import traceback as tb
from gettext import gettext as _

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

from MiAZ.backend.log import get_logger

class MiAZWidget(object):
    """Widget helper class for MiAZ widgets"""
    log = None

    def __init__(self, app, name=None):
        """Initialize Service instance"""
        # ~ GObject.GObject.__init__(self)
        self.app = app
        if name is None:
            name = __class__.__name__
        self.name = name
        self.log = get_logger(name)
