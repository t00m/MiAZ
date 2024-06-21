#!/usr/bin/python3
# File: about.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: About widget

from gi.repository import Gtk


class MiAZAbout(Gtk.Box):
    """
    About class
    """
    def __init__(self, app):
        super(Gtk.Box, self).__init__(spacing=12, orientation=Gtk.Orientation.VERTICAL)
        ENV = app.get_env()
        label = Gtk.Label()
        label.set_markup(f"{ENV['APP']['shortname']} {ENV['APP']['VERSION']}")
        self.append(label)

        # Set App desc
        label = Gtk.Label()
        label.set_markup(f"<big>{ENV['APP']['description']}</big>")
        self.append(label)

        # Set App license
        label = Gtk.Label()
        label.set_markup(f"<i>\n\n{ENV['APP']['license_long']}\n\n</i>")
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

