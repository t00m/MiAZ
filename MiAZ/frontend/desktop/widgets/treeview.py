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

from MiAZ.frontend.desktop.widgets.widget import MiAZWidget

class MiAZTreeView(MiAZWidget, Gtk.TreeView):
    """ Wrapper for Gtk.Stack with  with a StackSwitcher """
    __gtype_name__ = 'MiAZTreeView'

    def __init__(self, app):
        super().__init__(app, __class__.__name__)
        super(Gtk.TreeView, self).__init__()
        self.set_can_focus(True)
        self.set_enable_tree_lines(True)
        self.set_headers_visible(True)
        self.set_enable_search(True)
        self.set_hover_selection(False)
        self.set_grid_lines(Gtk.TreeViewGridLines.HORIZONTAL)
        self.selection = self.get_selection()
        # ~ self.selection.connect("changed", self.__row_changed)
        # ~ self.connect("changed", self.__row_changed)

    def __row_changed(self, treeview):
        self.log.debug(treeview)