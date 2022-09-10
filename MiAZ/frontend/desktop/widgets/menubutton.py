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


class MiAZMenuButton(Gtk.MenuButton):
    """
    Wrapper class for at Gtk.Menubutton with a menu defined
    in a Gtk.Builder xml string
    """

    def __init__(self, xml, name, icon_name='open-menu-symbolic'):
        super(MiAZMenuButton, self).__init__()
        builder = Gtk.Builder()
        builder.add_from_string(xml)
        menu = builder.get_object(name)
        self.set_menu_model(menu)
        self.set_icon_name(icon_name)
