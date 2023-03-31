#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
# File: icons.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Icon manager
"""

import os

import pkg_resources

import gi
gi.require_version('GdkPixbuf', '2.0')
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gdk
from gi.repository.GdkPixbuf import Pixbuf

from MiAZ.backend.log import get_logger
from MiAZ.backend.env import ENV

# FIXME: Review this module
class MiAZIconManager(GObject.GObject):
    def __init__(self, app):
        super(MiAZIconManager, self).__init__()
        self.app = app
        self.log = get_logger('ICM')
        self.util = self.app.backend.util
        win = Gtk.Window()
        self.theme = Gtk.IconTheme.get_for_display(win.get_display())
        self.theme.add_search_path(ENV['GPATH']['ICONS'])
        self.paintable = {}
        self.gicondict = {}
        self.icondict = {}
        self.pixbufdict = {}
        self.imgdict = {}

    def choose_icon(self, icon_list: list) -> str:
        found = 'unknown'
        for icon_name in icon_list:
            if self.theme.has_icon(icon_name):
                found = icon_name;
                break
        return found

    def get_pixbuf_by_name(self, name, width=48, height=48) -> Pixbuf:
        key = self.util.valid_key("%s-%d-%d" % (name, width, height))
        try:
            pixbuf = self.pixbufdict[key]
        except:
            paintable = self.theme.lookup_icon(name, None, width, 1, Gtk.TextDirection.NONE, Gtk.IconLookupFlags.FORCE_REGULAR)
            gfile = paintable.get_file()
            path = gfile.get_path()
            pixbuf = Pixbuf.new_from_file_at_size(path, width, height)
            self.pixbufdict[key] = pixbuf
        return pixbuf

    def get_image_by_name(self, name: str, width: int = 32, height: int = 32) -> Gtk.Image:
        pixbuf = self.get_pixbuf_by_name(name, width, height)
        return Gtk.Image.new_from_pixbuf(pixbuf)
