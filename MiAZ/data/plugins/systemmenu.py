#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: export2csv.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items to CSV
"""

import tempfile

from gi.repository import GObject
from gi.repository import Peas

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger


class MiAZSystemMenu(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZSystemMenu'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = get_logger('Plugin.SystemMenu')

    def do_activate(self):
        API = self.object
        self.app = API.app
        self.backend = self.app.get_service('backend')
        self.factory = self.app.get_factory()
        self.util = self.backend.util
        # ~ self.app.connect("headerbar-setup-finished", self.add_menuitem)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")
        API = self.object

    def add_menuitem(self, *args):
        self.log.debug(args)