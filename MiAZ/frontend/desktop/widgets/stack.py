#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from abc import abstractmethod

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw
from gi.repository import Gio
from gi.repository import GLib


class MiAZStack(Gtk.Stack):
    """ Wrapper for Gtk.Stack with  with a StackSwitcher """

    def __init__(self):
        super(MiAZStack, self).__init__()
        self.switcher = Gtk.StackSwitcher()
        self.switcher.set_stack(self)
        self._pages = {}

    def add_page(self, name, title, widget):
        page = self.add_child(widget)
        page.set_name(name)
        page.set_title(title)
        self._pages[name] = page
        return page

