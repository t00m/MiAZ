#!/usr/bin/python3
# File: help.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Help module with shortcuts used


from gettext import gettext as _
from gi.repository import Gtk
from gi.repository.Gtk import (
    ShortcutsGroup,
    ShortcutsSection,
    ShortcutsShortcut,
    ShortcutsWindow,
)

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


class SourceGroup(ShortcutsGroup):
    def __init__(self):
        super().__init__(title="Editor")

        self.add(ShortcutsShortcut(
            accelerator="<Control>c", title="Copy"))
        self.add(ShortcutsShortcut(
            accelerator="<Control>x", title="Cut"))
        self.add(ShortcutsShortcut(
            accelerator="<Control>v", title="Paste"))
        self.add(ShortcutsShortcut(
            accelerator="<Control>a", title="Select All"))
        self.add(ShortcutsShortcut(
            accelerator="<Control>Home", title="Go to Begin of Document"))
        self.add(ShortcutsShortcut(
            accelerator="<Control>End", title="Go to End of Document"))


class FindGroup(ShortcutsGroup):
    def __init__(self):
        super().__init__(title="Find")

        self.add(ShortcutsShortcut(
            accelerator="<Control>f",
            title="Find in Document / Find another match in same way"))
        self.add(ShortcutsShortcut(
            accelerator="<Control>g", title="Find next match"))
        self.add(ShortcutsShortcut(
            accelerator="<Shift><Control>g", title="Find previous match"))


class VimGroup(ShortcutsGroup):
    def __init__(self):
        super().__init__(title="Vim")

        self.add(ShortcutsShortcut(
            accelerator="y", title="Copy"))
        self.add(ShortcutsShortcut(
            accelerator="x", title="Cut"))
        self.add(ShortcutsShortcut(
            accelerator="p", title="Paste"))
        self.add(ShortcutsShortcut(
            accelerator="Escape+g+g", title="Go to Begin of Document"))
        self.add(ShortcutsShortcut(
            accelerator="Escape+<Shift>G", title="Go to End of Document"))
        self.add(ShortcutsShortcut(
            accelerator="Escape+g+g+<Shift>v+<Shift>G", title="Select All"))


class PreviewGroup(ShortcutsGroup):
    def __init__(self):
        super().__init__(title="Preview")

        self.add(ShortcutsShortcut(
            accelerator="<Control>r", title="Refresh preview"))
        self.add(ShortcutsShortcut(
            accelerator="<Alt>e", title="Show editor only"))
        self.add(ShortcutsShortcut(
            accelerator="<Alt>p", title="Show preview only"))
        self.add(ShortcutsShortcut(
            accelerator="<Alt>b", title="Show both"))


class GeneralGroup(ShortcutsGroup):
    def __init__(self, editor_type):
        super().__init__(title="Genaral")

        self.add(ShortcutsShortcut(
            accelerator="<Control>n", title="New Document"))
        self.add(ShortcutsShortcut(
            accelerator="<Control>o", title="Open Document"))
        self.add(ShortcutsShortcut(
            accelerator="<Control>s", title="Save Document"))
        self.add(ShortcutsShortcut(
            accelerator="<Shift><Control>s", title="Save Document As"))
        self.add(ShortcutsShortcut(
            accelerator="Escape+colon+w", title="Save Document Vim"))
        self.add(ShortcutsShortcut(
            accelerator="<Shift><Control>e", title="Export Document As"))
        self.add(ShortcutsShortcut(
            accelerator="<Control>p", title="Print Document"))
        self.add(ShortcutsShortcut(
            accelerator="<Control>w", title="Close Document"))
        self.add(ShortcutsShortcut(
            accelerator="<Control>q", title="Quit Formiko"))

class MiAZShortcutsWindow(ShortcutsWindow):
    def __init__(self):
        super().__init__(modal=1)
        sec = ShortcutsSection(title="MiAZ", visible=True, max_height=12)

        sec.add_group(GeneralGroup())
        sec.add_group(PreviewGroup())
        sec.add_group(FindGroup())
        sec.add_group(SourceGroup())
        sec.add_group(VimGroup())
        self.add_section(sec)
