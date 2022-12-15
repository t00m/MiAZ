#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Pango

from MiAZ.backend.env import ENV

class MiAZAbaout(Gtk.AboutDialog):
    def __init__(self, app):
        super(MiAZAbaout, self).__init__()
        self.app = app
        self.set_transient_for(self.app.win)
        self.set_modal(self)
        self.set_authors([ENV['APP']['author']])
        self.set_copyright(ENV['APP']['copyright'])
        self.set_license_type(Gtk.License.GPL_3_0)
        self.set_website(ENV['APP']['website'])
        self.set_website_label(ENV['APP']['name'])
        self.set_version(ENV['APP']['version'])
        self.set_logo_icon_name("MiAZ")
