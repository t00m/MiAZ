#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import shutil
from abc import abstractmethod

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Adw
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository.GdkPixbuf import Pixbuf
from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger



class MiAZAssistant(Gtk.Assistant):
    """ Start up Assistant"""

    def __init__(self, app):
        super(MiAZAssistant, self).__init__()
        self.log = get_logger('MiAZAssistant')
        self.app = app
        self.backend = self.app.get_backend()
        self.set_size_request(800, 600)
        self.set_title("MiAZ Assistant")

        # Page 0
        page0 = Gtk.Label.new(str='Label com a classe heading')
        page0.get_style_context().add_class(class_name='heading')
        # ~ page0.set_markup("This is a page")
        self.append_page(page0)
        self.set_page_title(page0, "Introduction")
        self.set_page_type(page0, Gtk.AssistantPageType.INTRO)
        self.set_page_complete(page0, True)

        # Page 1
        page1 = Gtk.Label()
        page1.set_markup("This is another page")
        self.append_page(page1)
        self.set_page_title(page1, "Confirm")
        self.set_page_type(page1, Gtk.AssistantPageType.CONFIRM)
        self.set_page_complete(page1, True)

        self.connect('cancel', self.on_assistant_cancel)
        self.connect('close', self.on_assistant_close)

    def on_assistant_cancel(self, *args):
        self.destroy()
        self.app.win.present()

    def on_assistant_close(self, *args):
        self.destroy()
        self.app.win.present()
