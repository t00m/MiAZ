#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from abc import abstractmethod
import json

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw
from gi.repository import Gio
from gi.repository import GLib

from MiAZ.backend.env import ENV
# ~ from MiAZ.frontend.desktop.widgets.widget import MiAZWidget
# ~ from MiAZ.frontend.desktop.widgets.treeview import MiAZTreeView
from MiAZ.frontend.desktop.widgets.configview import MiAZConfigView

class MiAZCollections(MiAZConfigView):
    """Class for managing Collections from Settings"""
    __gtype_name__ = 'MiAZCollections'
    current = None

    def __init__(self, app):
        super().__init__(app)

