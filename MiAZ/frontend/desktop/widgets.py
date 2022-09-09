#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw
from gi.repository import Gio
from gi.repository import GLib


# Gtk.Builder xml for the application menu
MiAZ_APP_MENU = """
<?xml version="1.0" encoding="UTF-8"?>
<interface>
<menu id='app-menu'>
  <section>
    <item>
      <attribute name='label' translatable='yes'>_New Stuff</attribute>
      <attribute name='action'>win.new</attribute>
    </item>
    <item>
      <attribute name='label' translatable='yes'>_About</attribute>
      <attribute name='action'>win.about</attribute>
    </item>
    <item>
      <attribute name='label' translatable='yes'>_Shortcuts</attribute>
      <attribute name='action'>win.shortcuts</attribute>
    </item>
    <item>
      <attribute name='label' translatable='yes'>_Quit</attribute>
      <attribute name='action'>win.quit</attribute>
    </item>
  </section>
</menu>
</interface>
"""

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
