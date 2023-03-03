#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: about.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: About widget
"""

from html import escape
from gettext import gettext as _

import gi
from gi.repository import Adw
from gi.repository import Gtk

from MiAZ.backend.env import ENV


class MiAZAbout(Gtk.Box):
    """
    About class
    """
    def __init__(self, app):
        super(Gtk.Box, self).__init__(spacing=12, orientation=Gtk.Orientation.VERTICAL)
        widget = Adw.StatusPage.new()
        widget.set_title(title="%s %s" % (ENV['APP']['shortname'].capitalize(), ENV['APP']['version']))
        widget.set_icon_name(icon_name='MiAZ-big')
        # ~ widget.set_hexpand(True)
        # ~ widget.set_vexpand(True)

        # ~ # Set logo
        # ~ label = Gtk.Label()
        # ~ widget.append(label)

        # ~ # Set App name
        # ~ label = Gtk.Label()
        # ~ label.set_markup("<big><b>%s %s</b></big>" % (ENV['APP']['shortname'].capitalize(), ENV['APP']['version']))
        # ~ widget.append(label)

        # ~ # Set App desc
        # ~ label = Gtk.Label()
        # ~ label.set_markup("%s" % ENV['APP']['description'])
        # ~ widget.append(label)

        # ~ # Set App license
        # ~ label = Gtk.Label()
        # ~ label.set_markup("<i>\n\n%s\n%s\n\n</i>" % (ENV['APP']['license'], ENV['APP']['license_long']))
        # ~ label.set_justify(Gtk.Justification.CENTER)
        # ~ widget.append(label)

        # ~ # Set Link button
        # ~ linkbutton = Gtk.LinkButton(uri="https://github.com/t00m/Basico", label="https://github.com/t00m/Basico")
        # ~ widget.append(linkbutton)

        # ~ # Set Copyright holders
        # ~ label = Gtk.Label()
        # ~ label.set_markup(ENV['APP']['copyright'])
        # ~ label.set_justify(Gtk.Justification.CENTER)
        # ~ widget.append(label)

        # ~ # Authors
        # ~ label = Gtk.Label()
        # ~ label.set_markup("\n%s" % escape(ENV['APP']['author']))
        # ~ label.set_justify(Gtk.Justification.CENTER)
        # ~ label.set_selectable(True)
        # ~ widget.append(label)

        self.append(widget)

