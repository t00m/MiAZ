#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
# File: icons.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Icon manager
"""

import os

from gi.repository import Gtk
from gi.repository import Gio
from gi.repository import GObject
from gi.repository.GdkPixbuf import Pixbuf

from MiAZ.backend.log import get_logger

# FIXME: Review this module
class MiAZIconManager(GObject.GObject):
    def __init__(self, app):
        super(MiAZIconManager, self).__init__()
        self.app = app
        ENV = self.app.get_env()
        self.log = get_logger('MiAZ.IconManager')
        self.util = self.app.backend.get_service('util')
        win = Gtk.Window()
        self.theme = Gtk.IconTheme.get_for_display(win.get_display())
        self.log.debug("Custom icons in: %s", ENV['GPATH']['ICONS'])
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
                found = icon_name
                break
        return found

    def get_pixbuf_by_name(self, name, width=24, height=24) -> Pixbuf:
        key = self.util.valid_key("%s-%d-%d" % (name, width, height))
        try:
            pixbuf = self.pixbufdict[key]
        except KeyError:
            try:
                paintable = self.theme.lookup_icon(name, None, width, 1, Gtk.TextDirection.NONE, Gtk.IconLookupFlags.FORCE_REGULAR)
                gfile = paintable.get_file()
                path = gfile.get_path()
                pixbuf = Pixbuf.new_from_file_at_size(path, width, height)
                self.pixbufdict[key] = pixbuf
            except TypeError:
                pixbuf = self.get_pixbuf_by_name('folder', width)

        return pixbuf

    def get_image_by_name(self, name: str, width: int = 24, height: int = 24) -> Gtk.Image:
        pixbuf = self.get_pixbuf_by_name(name, width, height)
        return Gtk.Image.new_from_pixbuf(pixbuf)

    def get_mimetype_icon(self, mimetype: str) -> Gtk.Image:
        try:
            gicon = self.gicondict[mimetype]
        except Exception:
            gicon = Gio.content_type_get_icon(mimetype)
            self.gicondict[mimetype] = gicon
        return gicon

    def get_flag_icon(self, code: str) -> Gtk.Image:
        ENV = self.app.get_env()
        try:
            paintable = self.paintable[code]
        except Exception:
            iconpath = os.path.join(ENV['GPATH']['FLAGS'], "%s.svg" % code)
            if not os.path.exists(iconpath):
                iconpath = os.path.join(ENV['GPATH']['FLAGS'], "__.svg")
            image = Gtk.Image()
            image.set_from_file(iconpath)
            paintable = image.get_paintable()
            self.paintable[code] = paintable
        return paintable

    def get_gicon(self, name:str):
        gicon = Gio.Icon.new_for_string(name)
        self.log.debug(gicon)
        return gicon
