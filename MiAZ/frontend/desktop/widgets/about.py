#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: about.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: About widget
"""

from gettext import gettext as _

import gi
from gi.repository import Gtk

from MiAZ.backend.env import ENV


class MiAZAbout(Gtk.Box):
    """
    About class
    """
    def __init__(self, app):
        super(Gtk.Box, self).__init__(spacing=12, orientation=Gtk.Orientation.VERTICAL)
        label = Gtk.Label()
        label.set_markup("%s %s" % (ENV['APP']['shortname'], ENV['APP']['version']))
        # ~ widget.set_icon_name(icon_name='MiAZ-big')
        self.append(label)

        # Set App desc
        label = Gtk.Label()
        label.set_markup("<big>%s</big>" % ENV['APP']['description'])
        self.append(label)

        # Set App license
        label = Gtk.Label()
        label.set_markup("<i>\n\n%s\n\n</i>" % ENV['APP']['license_long'])
        label.set_justify(Gtk.Justification.CENTER)
        self.append(label)

        # Set Link button
        linkbutton = Gtk.LinkButton(uri="https://github.com/t00m/MiAZ", label="https://github.com/t00m/MiAZ")
        self.append(linkbutton)

        # Set Copyright holders
        label = Gtk.Label()
        label.set_markup(ENV['APP']['copyright'])
        label.set_justify(Gtk.Justification.CENTER)
        self.append(label)

