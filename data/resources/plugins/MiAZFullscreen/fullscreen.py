# pylint: disable=E1101

"""
# File: fullscreen.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Fullscreen toggle button plugin
"""

from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gdk
from gi.repository import Gtk

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

plugin_info = {
        'Module':        'fullscreen',
        'Name':          'MiAZFullscreen',
        'Loader':        'Python3',
        'Description':   _('Toggle fullscreen'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2025 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'http://github.com/t00m/MiAZ/README.adoc',
        'Version':       '0.1.26',
        'Category':      'Customisation and Personalisation',
        'Subcategory':   'User Interface'
    }

BUTTON_WIDGET_ID = 'headerbar-togglebutton-fullscreen'
UI_GROUP_WIDGET_ID = 'window-preferences-page-ui-group'
ICON_ENTER = 'view-fullscreen-symbolic'
ICON_LEAVE = 'view-restore-symbolic'


class MiAZFullscreenPlugin(MiAZExtension):
    __gtype_name__ = 'MiAZFullscreenPlugin'
    plugin = None

    def do_activate(self):
        """Plugin activation"""
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)
        self.plugin.register(self, plugin_info)
        self.log = self.plugin.get_logger()
        self.actions = self.app.get_service('actions')
        self.factory = self.app.get_service('factory')

        # Add a row in the User Interface preferences group whenever the
        # Preferences dialog is opened (same pattern as MiAZWSFont).
        self._settings_handler = self.actions.connect(
            'settings-loaded', self._on_settings_loaded)

        self.workspace = self.app.get_widget('workspace')
        if self.workspace.is_loaded():
            self.startup()
        else:
            self._startup_handler = self.workspace.connect(
                'workspace-loaded', self.startup)

    def do_deactivate(self):
        # The header bar button is detached by the plugin system, which owns
        # what add_headerbar_widget handed it.
        window = self.app.get_widget('window')
        if window is not None and hasattr(self, '_fullscreen_handler'):
            window.disconnect(self._fullscreen_handler)
        evk = self.app.get_widget('window-event-controller')
        if evk is not None and hasattr(self, '_key_handler'):
            evk.disconnect(self._key_handler)
        if hasattr(self, '_startup_handler'):
            self.workspace.disconnect(self._startup_handler)
        if getattr(self, '_settings_handler', None) is not None:
            self.actions.disconnect(self._settings_handler)
            self._settings_handler = None
        self.plugin.set_started(False)

    def startup(self, *args):
        if self.plugin.started():
            return

        button = self.app.get_widget(BUTTON_WIDGET_ID)
        if button is None:
            button = Gtk.ToggleButton()
            button.set_icon_name(ICON_ENTER)
            button.set_has_frame(False)
            button.set_valign(Gtk.Align.CENTER)
            button.set_hexpand(False)
            button.set_tooltip_text(_('Enter fullscreen'))
            self._toggled_handler = button.connect('toggled', self._on_toggle)

            visible = self.plugin.get_config_key('icon_visible')
            if visible is None:
                visible = True
                self.plugin.set_config_key('icon_visible', True)
            button.set_visible(visible)
            # The plugin system detaches the button and drops its widget key
            # when this plugin is unloaded, so the next activation builds a
            # fresh one instead of finding a stale key and doing nothing.
            self.plugin.add_headerbar_widget(
                button, position='left', widget_key=BUTTON_WIDGET_ID)

            # Keep the button in sync when fullscreen is toggled elsewhere
            # (window manager, F11) and reflect the current window state.
            window = self.app.get_widget('window')
            self._fullscreen_handler = window.connect(
                'notify::fullscreened', self._on_fullscreen_changed)
            self._sync_button(window.is_fullscreen())

            # F11 is the conventional fullscreen shortcut.
            evk = self.app.get_widget('window-event-controller')
            if evk is not None:
                self._key_handler = evk.connect('key-pressed', self._on_key_press)

            self.log.debug("Plugin fullscreen activated")

        self.plugin.set_started(started=True)

    def _on_toggle(self, button, *args):
        window = self.app.get_widget('window')
        if window is None:
            return
        if button.get_active():
            window.fullscreen()
        else:
            window.unfullscreen()

    def _on_fullscreen_changed(self, window, gparam):
        self._sync_button(window.is_fullscreen())

    def _sync_button(self, is_fullscreen):
        """Reflect the window state on the button without re-triggering it."""
        button = self.app.get_widget(BUTTON_WIDGET_ID)
        if button is None:
            return
        if hasattr(self, '_toggled_handler'):
            button.handler_block(self._toggled_handler)
            button.set_active(is_fullscreen)
            button.handler_unblock(self._toggled_handler)
        else:
            button.set_active(is_fullscreen)
        button.set_icon_name(ICON_LEAVE if is_fullscreen else ICON_ENTER)
        button.set_tooltip_text(
            _('Leave fullscreen') if is_fullscreen else _('Enter fullscreen'))

    def _on_key_press(self, event, keyval, keycode, state):
        if Gdk.keyval_name(keyval) == 'F11':
            button = self.app.get_widget(BUTTON_WIDGET_ID)
            if button is not None:
                button.set_active(not button.get_active())
            return True
        return False

    def _on_settings_loaded(self, actions, dialog_app_settings):
        group = self.app.get_widget(UI_GROUP_WIDGET_ID)
        if group is None:
            self.log.warning(
                "User Interface preferences group not found; "
                "skipping fullscreen-toggle row")
            return
        visible = self.plugin.get_config_key('icon_visible')
        if visible is None:
            visible = True
        row = Adw.SwitchRow(title=_('Display fullscreen toggle button'))
        row.set_active(bool(visible))
        row.connect('notify::active', self._on_activate_setting)
        group.add(row)

    def _on_activate_setting(self, row, gparam):
        visible = row.get_active()
        button = self.app.get_widget(BUTTON_WIDGET_ID)
        if button is not None:
            button.set_visible(visible)
        self.plugin.set_config_key('icon_visible', visible)
