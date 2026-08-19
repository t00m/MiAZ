# pylint: disable=E1101

"""
# File: colvis.py
# Author: Tomas Virseda
# License: GPL v3
# Description: Column visibility plugin for workspace
"""

from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gdk
from gi.repository import Gtk

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

UI_GROUP_WIDGET_ID = 'window-preferences-page-ui-group'

plugin_info = {
    'Module':        'colvis',
    'Name':          'MiAZColumnVisibility',
    'Loader':        'Python3',
    'Description':   _('Toggle workspace column visibility'),
    'Authors':       'Tomas Virseda <tomasvirseda@gmail.com>',
    'Copyright':     'Copyright © 2025 Tomas Virseda',
    'Website':       'http://github.com/t00m/MiAZ',
    'Help':          'https://github.com/t00m/MiAZ/blob/main/README.md',
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
    # Set in startup(), cleared in do_deactivate(). A right click can arrive
    # in between, so the handler checks it rather than assuming it is there.
    popover = None
    gesture = None
    cv = None
    _startup_handler = None

    def do_activate(self):
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)
        self.plugin.register(self, plugin_info)
        self.log = self.plugin.get_logger()
        self.factory = self.app.get_service('factory')
        self.actions = self.app.get_service('actions')
        self.workspace = self.app.get_widget('workspace')
        # Add a configuration entry under App Settings > User Interface.
        self._settings_handler = self.actions.connect('settings-loaded', self._on_settings_loaded)
        if self.workspace.is_loaded():
            self.startup()
        else:
            self._startup_handler = self.workspace.connect('workspace-loaded', self.startup)

    def do_deactivate(self):
        # Drop the controller and forget it. Keeping the attribute around let a
        # second deactivate try to remove a controller that is already gone.
        if getattr(self, 'gesture', None) is not None:
            if getattr(self, 'cv', None) is not None:
                self.cv.remove_controller(self.gesture)
            self.gesture = None
            self.cv = None
        if getattr(self, 'popover', None) is not None:
            self.popover.unparent()
            self.popover = None
        if getattr(self, '_startup_handler', None) is not None:
            self.workspace.disconnect(self._startup_handler)
            self._startup_handler = None
        if getattr(self, '_settings_handler', None) is not None:
            self.actions.disconnect(self._settings_handler)
            self._settings_handler = None
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
        # The plugin can be deactivated while this gesture is still attached to
        # a column view that outlives it (a repository switch unloads every
        # plugin). Without the popover there is nothing to show or hide, and
        # the click belongs to whoever is still listening.
        if self.popover is None:
            return

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
        self._set_column_visible(attr, check.get_active())

    def _set_column_visible(self, attr, active):
        """Apply and persist the visibility of a single column."""
        wsview = self.workspace.get_workspace_view()
        if wsview is None:
            return
        column = getattr(wsview, attr, None)
        if column is not None:
            column.set_visible(active)
            config = self.plugin.get_config_data()
            config[attr] = active
            self.plugin.set_config_data(config)

    def _on_settings_loaded(self, actions, dialog_app_settings):
        """Add column visibility switches to App Settings > User Interface."""
        group = self.app.get_widget(UI_GROUP_WIDGET_ID)
        if group is None:
            self.log.warning(
                "User Interface preferences group not found; "
                "skipping column-visibility rows")
            return
        wsview = self.workspace.get_workspace_view()
        if wsview is None:
            return

        expander = Adw.ExpanderRow(title=_('Workspace columns'))
        expander.set_subtitle(_('Show or hide columns in the Documents view'))
        for attr, label_text in COLUMNS.items():
            column = getattr(wsview, attr, None)
            if column is None:
                continue
            row = Adw.SwitchRow(title=label_text)
            row.set_active(column.get_visible())
            row.connect('notify::active', self._on_column_switch, attr)
            expander.add_row(row)
        group.add(expander)

    def _on_column_switch(self, row, gparam, attr):
        self._set_column_visible(attr, row.get_active())
