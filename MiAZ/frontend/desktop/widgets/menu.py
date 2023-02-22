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


# Gtk.Builder xml for the application menu
MiAZ_MENU_APP = """
<?xml version="1.0" encoding="UTF-8"?>
<interface>
<menu id='app-menu'>
  <section>
    <item>
      <attribute name='label' translatable='yes'>Settings</attribute>
      <attribute name='action'>app.settings_app</attribute>
    </item>
    <item>
      <attribute name='label' translatable='yes'>Help</attribute>
      <attribute name='action'>app.help</attribute>
    </item>
    <item>
      <attribute name='label' translatable='yes'>_About</attribute>
      <attribute name='action'>app.about</attribute>
    </item>
    <item>
      <attribute name='label' translatable='yes'>_Quit</attribute>
      <attribute name='action'>app.close</attribute>
    </item>
  </section>
</menu>
</interface>
"""

MiAZ_MENU_REPO = """
<?xml version="1.0" encoding="UTF-8"?>
<interface>
<menu id='repo-menu'>
  <section>
    <item>
      <attribute name='label' translatable='yes'>Repo settings</attribute>
      <attribute name='action'>app.repo_settings</attribute>
      <attribute name="verb-icon">document-properties</attribute>
    </item>
    <item>
      <attribute name='label' translatable='yes'>Backup</attribute>
      <attribute name='action'>app.backup</attribute>
    </item>
  </section>
  <section>
    <item>
      <attribute name='label' translatable='yes'>Delete</attribute>
      <attribute name='action'>app.delete</attribute>
    </item>
  </section>
</menu>
</interface>
"""

MiAZ_MENU_DOCUMENT = """
<?xml version="1.0" encoding="UTF-8"?>
<interface>
<menu id='repo-menu'>
  <section>
    <item>
      <attribute name='label' translatable='yes'>Rename</attribute>
      <attribute name='action'>app.doc_rename</attribute>
    </item>
    <item>
      <attribute name='label' translatable='yes'>Backup</attribute>
      <attribute name='action'>app.backup</attribute>
    </item>
    <item>
      <attribute name='label' translatable='no'>--</attribute>
      <attribute name='action'></attribute>
    </item>
    <item>
      <attribute name='label' translatable='yes'>Delete</attribute>
      <attribute name='action'>app.delete</attribute>
    </item>
  </section>
</menu>
</interface>
"""
