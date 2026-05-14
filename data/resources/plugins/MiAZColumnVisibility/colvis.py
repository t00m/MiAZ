#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: colvis.py
# Author: Tomas Virseda
# License: GPL v3
# Description: Column visibility plugin for workspace
"""

from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Gtk

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

plugin_info = {
    'Module':        'colvis',
    'Name':          'MiAZColumnVisibility',
    'Loader':        'Python3',
    'Description':   _('Toggle workspace column visibility'),
    'Authors':       'Tomas Virseda <tomasvirseda@gmail.com>',
    'Copyright':     'Copyright © 2025 Tomas Virseda',
    'Website':       'http://github.com/t00m/MiAZ',
    'Help':          'http://github.com/t00m/MiAZ/README.adoc',
    'Version':       '0.1.26',
    'Category':      'Customisation and Personalisation',
    'Subcategory':   'User Interface'
}

COLUMNS = {
    'column_date':      _('Date'),
    'column_country':   _('Country'),
    'column_flag':      _('Flag'),
    'column_icon_type': _('Type'),
    'column_group':     _('Group'),
    'column_purpose':   _('Purpose'),
    # ~ 'column_title':     _('Title'),
    'column_subtitle':  _('Concept'),
    'column_sentby':    _('Sent by'),
    'column_sentto':    _('Sent to'),
    'column_extension': _('Extension'),
}


class MiAZColumnVisibilityPlugin(MiAZExtension):
    __gtype_name__ = 'MiAZColumnVisibilityPlugin'
    plugin = None

    def do_activate(self):
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)
        self.plugin.register(self, plugin_info)
        self.log = self.plugin.get_logger()
        self.factory = self.app.get_service('factory')
        self.workspace = self.app.get_widget('workspace')
        if self.workspace.is_loaded():
            self.startup()
        else:
            self._startup_handler = self.workspace.connect('workspace-loaded', self.startup)

    def do_deactivate(self):
        if hasattr(self, 'cv') and hasattr(self, 'gesture'):
            self.cv.remove_controller(self.gesture)
        if hasattr(self, 'popover'):
            self.popover.unparent()
            self.popover = None
        if hasattr(self, '_startup_handler'):
            self.workspace.disconnect(self._startup_handler)
        self.plugin.set_started(False)

    def startup(self, *args):
        if not self.plugin.started():
            wsview = self.workspace.get_workspace_view()
            self.cv = wsview.cv

            self.gesture = Gtk.GestureClick.new()
            self.gesture.set_button(3)
            self.gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
            self.gesture.connect('pressed', self._on_right_click)
            self.cv.add_controller(self.gesture)

            self.popover = Gtk.Popover()
            self.popover.set_parent(self.workspace)
            self.popover.set_has_arrow(False)
            self.popover.set_autohide(True)

            config = self.plugin.get_config_data()
            if config:
                for attr in COLUMNS:
                    column = getattr(wsview, attr, None)
                    if column is not None and attr in config:
                        column.set_visible(config[attr])

            self.plugin.set_started(True)
            self.log.debug("Plugin colvis activated")

    def _build_popover_content(self):
        wsview = self.workspace.get_workspace_view()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        vbox.set_margin_top(6)
        vbox.set_margin_bottom(6)
        vbox.set_margin_start(6)
        vbox.set_margin_end(6)

        title = Gtk.Label()
        title.set_markup('<b>' + _('Column visibility') + '</b>')
        title.set_margin_bottom(6)
        vbox.append(title)

        for attr, label_text in COLUMNS.items():
            column = getattr(wsview, attr, None)
            if column is None:
                continue
            check = Gtk.CheckButton(label=label_text)
            check.set_active(column.get_visible())
            check.connect('toggled', self._on_toggle_column, attr)
            vbox.append(check)

        return vbox

    def _on_right_click(self, gesture, n_press, x, y):
        # Only handle clicks in the column header area (~top 50px).
        # Row-click right-clicks are left for the existing selection menu.
        if y > 50:
            self.popover.popdown()
            return

        gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        self.popover.set_child(self._build_popover_content())

        rect = Gdk.Rectangle()
        rect.x = int(x)
        rect.y = int(y)
        rect.width = 1
        rect.height = 1
        self.popover.set_pointing_to(rect)
        self.popover.popup()

    def _on_toggle_column(self, check, attr):
        wsview = self.workspace.get_workspace_view()
        column = getattr(wsview, attr, None)
        if column is not None:
            column.set_visible(check.get_active())
            config = self.plugin.get_config_data()
            config[attr] = check.get_active()
            self.plugin.set_config_data(config)
