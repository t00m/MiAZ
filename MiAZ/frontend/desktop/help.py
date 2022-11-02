#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gettext import gettext as _
from gi.repository import Gtk


SHORTCUTS = [
    (_("Main Window"), [
        ('<Ctrl>h', _("Help")),
        ('<Ctrl>a', _("About this application")),
        ('<Ctrl>q', _("Quit application")),
    ]),
    (_("Workspace"), [
        ('<Ctrl>v', _("View document")),
        ('<Ctrl>r', _("Rename document")),
        ('<Ctrl>d', _("Delete document")),
    ]),
]



def build_shortcut_window(data):
    """Returns a filled Gtk.ShortcutsWindow"""
    w = Gtk.ShortcutsWindow()
    section = Gtk.ShortcutsSection()
    section.show()
    for group_title, shortcuts in data:
        group = Gtk.ShortcutsGroup(title=group_title)
        group.show()
        for accel, shortcut_title in shortcuts:
            short = Gtk.ShortcutsShortcut(
                title=shortcut_title, accelerator=accel)
            short.show()
            group.append(short)
        section.append(group)
    w.set_child(section)
    return w


def show_shortcuts(parent):
    window = build_shortcut_window(SHORTCUTS)
    window.set_transient_for(parent)
    window.set_modal(True)
    window.present()

