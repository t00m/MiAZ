# pylint: disable=E1101

"""
# File: wsfont.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Workspace font plugin manager
"""

from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import Pango

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

plugin_info = {
        'Module':        'wsfont',
        'Name':          'MiAZWSFont',
        'Loader':        'Python3',
        'Description':   _('Modify Workspace font name and size'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2025 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'https://github.com/t00m/MiAZ/blob/main/README.md',
        'Version':       '0.1',
        'Category':      'Interface',
        'Subcategory':   'Accessibility'
    }

DEFAULT_FONT_FAMILY = 'Monospace'
DEFAULT_FONT_SIZE = 12
MIN_FONT_SIZE = 8
MAX_FONT_SIZE = 48
UI_GROUP_WIDGET_ID = 'window-preferences-page-ui-group'


class MiAZWSFontPlugin(MiAZExtension):
    __gtype_name__ = 'MiAZWSFontPlugin'
    plugin = None

    def do_activate(self):
        """Plugin activation"""
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)
        self.plugin.register(self, plugin_info)
        self.log = self.plugin.get_logger()
        self.actions = self.app.get_service('actions')
        self.factory = self.app.get_service('factory')
        self.workspace = self.app.get_widget('workspace')
        self._css_provider = None
        self._startup_handler = None
        self._settings_handler = self.actions.connect(
            'settings-loaded', self._on_settings_loaded)

        if self.workspace.is_loaded():
            self.startup()
        else:
            self._startup_handler = self.workspace.connect(
                'workspace-loaded', self.startup)

    def do_deactivate(self):
        if self._css_provider is not None and self.workspace is not None:
            display = self.workspace.get_display()
            try:
                Gtk.StyleContext.remove_provider_for_display(
                    display, self._css_provider)
            except Exception:
                pass
            wsview = self.workspace.get_workspace_view()
            if wsview is not None:
                wsview.remove_css_class('custom-font')
            self._css_provider = None
        if self._startup_handler is not None:
            self.workspace.disconnect(self._startup_handler)
            self._startup_handler = None
        if self._settings_handler is not None:
            self.actions.disconnect(self._settings_handler)
            self._settings_handler = None
        self.plugin.set_started(False)

    def startup(self, *args):
        if not self.plugin.started():
            family, size = self._read_font_config()
            self._apply_font(family, size)
            self.plugin.set_started(True)

    def _read_font_config(self):
        family = self.plugin.get_config_key('font-family')
        if not family:
            family = DEFAULT_FONT_FAMILY
        size = self.plugin.get_config_key('font-size')
        try:
            size = int(size)
        except (TypeError, ValueError):
            size = DEFAULT_FONT_SIZE
        if size < MIN_FONT_SIZE or size > MAX_FONT_SIZE:
            size = DEFAULT_FONT_SIZE
        return family, size

    def _apply_font(self, family, size):
        wsview = self.workspace.get_workspace_view()
        if wsview is None:
            return
        safe_family = family.replace("'", "\\'")
        css = (
            ".custom-font {\n"
            "    font-family: '%s';\n"
            "    font-size: %dpx;\n"
            "}\n" % (safe_family, size)
        )
        if self._css_provider is None:
            self._css_provider = Gtk.CssProvider()
            Gtk.StyleContext.add_provider_for_display(
                self.workspace.get_display(),
                self._css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        self._css_provider.load_from_data(css.encode())
        wsview.add_css_class('custom-font')
        self.plugin.set_config_key('font-family', family)
        self.plugin.set_config_key('font-size', size)

    def _on_settings_loaded(self, actions, dialog_app_settings):
        group = self.app.get_widget(UI_GROUP_WIDGET_ID)
        if group is None:
            self.log.warning(
                "User Interface preferences group not found; "
                "skipping workspace-font rows")
            return
        family, size = self._read_font_config()

        row_family = Adw.ActionRow(title=_('Workspace font family'))
        font_dialog = Gtk.FontDialog()
        font_dialog.set_title(_('Choose workspace font family'))
        font_button = Gtk.FontDialogButton(dialog=font_dialog)
        font_button.set_level(Gtk.FontLevel.FAMILY)
        font_button.set_valign(Gtk.Align.CENTER)
        font_button.set_font_desc(Pango.FontDescription.from_string(family))
        font_button.connect('notify::font-desc', self._on_family_changed)
        row_family.add_suffix(font_button)
        row_family.set_activatable_widget(font_button)
        group.add(row_family)

        adj = Gtk.Adjustment(
            value=size,
            lower=MIN_FONT_SIZE,
            upper=MAX_FONT_SIZE,
            step_increment=1,
            page_increment=2,
        )
        row_size = Adw.SpinRow(
            title=_('Workspace font size'),
            adjustment=adj,
            digits=0,
        )
        row_size.connect('notify::value', self._on_size_changed)
        group.add(row_size)

    def _on_family_changed(self, button, gparam):
        desc = button.get_font_desc()
        family = (desc.get_family() if desc is not None else None) or DEFAULT_FONT_FAMILY
        _f, size = self._read_font_config()
        self._apply_font(family, size)

    def _on_size_changed(self, row, gparam):
        size = int(row.get_value())
        family, _s = self._read_font_config()
        self._apply_font(family, size)
