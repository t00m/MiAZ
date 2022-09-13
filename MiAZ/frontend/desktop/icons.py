#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
# File: srv_iconmgt.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Icon manager service
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

from MiAZ.backend.env import ENV
from MiAZ.frontend.desktop.util import get_file_mimetype
from MiAZ.backend.util import valid_key

# FIXME: Fix caching system for pixbufs

class MiAZIconManager(GObject.GObject):
    def __init__(self, win):
        super(MiAZIconManager, self).__init__()
        self.win = win
        self.theme = Gtk.IconTheme.get_for_display(self.win.get_display())
        self.theme.add_search_path(ENV['GPATH']['ICONS'])
        self.paintable = {}
        self.gicondict = {}
        self.icondict = {}
        self.pixbufdict = {}
        self.imgdict = {}

    def get_gicon_from_file_mimetype(self, mimetype: str) -> Gio.Icon:
        try:
            gicon = self.gicondict[mimetype]
        except KeyError:
            gicon = Gio.content_type_get_icon(mimetype)
            self.gicondict[mimetype] = gicon
            # ~ print("Cached gicon for mimetype: %s" % mimetype)
        return gicon

    def get_paintable_from_gicon(self, gicon: Gio.Icon) -> Gdk.Paintable:
        try:
            paintable = self.paintable[gicon]
        except KeyError:
            paintable = self.theme.lookup_by_gicon(gicon, 64, 1, Gtk.TextDirection.NONE, Gtk.IconLookupFlags.FORCE_REGULAR)
            self.paintable[gicon] = paintable
            # ~ print("Cached paintable for gicon: %s" % gicon)
        return paintable

    def get_pixbuf_from_file_at_size(self, filepath, width=48, height=48) -> Pixbuf:
        key = valid_key("%s-%d-%d" % (filepath, width, height))
        try:
            pixbuf = self.pixbufdict[key]
        except KeyError:
            pixbuf = Pixbuf.new_from_file_at_size(filepath, width, height)
            self.pixbufdict[key] = pixbuf
            # ~ print("Cached pixbuf: %s" % pixbuf)
        return pixbuf

    def get_pixbuf_mimetype_from_file(self, filepath, width=48, height=48) -> Pixbuf:
        mimetype = get_file_mimetype(filepath)
        key = valid_key("%s-%d-%d" % (mimetype, width, height))
        try:
            pixbuf = self.pixbufdict[key]
        except KeyError:
            gicon = self.get_gicon_from_file_mimetype(mimetype)
            paintable = self.get_paintable_from_gicon(gicon)
            gfile = paintable.get_file()
            path = gfile.get_path()
            if path is None:
                pixbuf = self.get_pixbuf_by_name('text-x-generic-symbolic', width)
            else:
                pixbuf = Pixbuf.new_from_file_at_size(path, width, height)
            self.pixbufdict[key] = pixbuf
            # ~ print("Cached pixbuf for mimetype: %s" % mimetype)
        return pixbuf

    def get_pixbuf_by_name(self, name, width=48, height=48) -> Pixbuf:
        key = valid_key("%s-%d-%d" % (name, width, height))
        try:
            pixbuf = self.pixbufdict[key]
        except:
            paintable = self.theme.lookup_icon(name, None, width, 1, Gtk.TextDirection.NONE, Gtk.IconLookupFlags.FORCE_REGULAR)
            gfile = paintable.get_file()
            path = gfile.get_path()
            pixbuf = Pixbuf.new_from_file_at_size(path, width, height)
            self.pixbufdict[key] = pixbuf
            # ~ print("Cached pixbuf for name: %s" % name)
        return pixbuf

