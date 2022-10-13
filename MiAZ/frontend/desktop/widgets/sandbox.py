#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository.GdkPixbuf import Pixbuf

from MiAZ.backend.log import get_logger
from MiAZ.frontend.desktop.widgets.listview import MyListView
from MiAZ.frontend.desktop.widgets.listview import ListElemRow


class MiAZSandBox(Gtk.Box):
    """ MiAZ SandBox Widget"""

    def __init__(self, app):
        super(MiAZSandBox, self).__init__(spacing=12, orientation=Gtk.Orientation.VERTICAL)
        self.log = get_logger('MiAZSandBox')
        self.app = app
        self.backend = self.app.get_backend()
        self.set_vexpand(True)
        listview = MyListView(self.app.win)
        self.append(listview)
        # ~ listview.add(ListElemRow("One"))
