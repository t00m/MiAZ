#!/usr/bin/python3
# File: help.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Help module with shortcuts used


from gettext import gettext as _
from gi.repository import Gtk

SHORTCUTS = [
    (_("Main Window"), [
        ('<Ctrl>h', _("Help")),
        ('<Ctrl>q', _("Quit application")),
    ]),
    (_("Workspace"), [
        ('<Ctrl>d', _("Display document")),
        ('<Ctrl>r', _("Rename document")),
    ]),
]


class MiAZHelp(Gtk.Box):
    """
    Help class
    """
    def __init__(self, app):
        super(Gtk.Box, self).__init__(spacing=12, orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True)
        box = Gtk.CenterBox()
        section = Gtk.ShortcutsSection()
        section.show()
        for group_title, shortcuts in SHORTCUTS:
            group = Gtk.ShortcutsGroup(title=group_title)
            group.show()
            for accel, shortcut_title in shortcuts:
                short = Gtk.ShortcutsShortcut(
                    title=shortcut_title, accelerator=accel)
                short.show()
                group.append(short)
            section.append(group)
        box.set_center_widget(section)
        self.append(box)
