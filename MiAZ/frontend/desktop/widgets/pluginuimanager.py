import os
import requests
from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import GObject

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import Plugin
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewPlugin
from MiAZ.frontend.desktop.widgets.window import MiAZCustomWindow
from MiAZ.backend.pluginsystem import MiAZPluginType

TOKEN_PLUGINS_REPO_READ_ONLY = "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"

class MiAZPluginUIManager(MiAZCustomWindow):
    __gtype_name__ = 'MiAZPluginUIManager'

    def __init__(self, app, **kwargs):
        self.app = app
        self.log = MiAZLog('MiAZ.MiAZPluginUIManager')
        self.name = 'plugin-ui-manager'

        self.title = f"Plugin Manager"
        super().__init__(app, self.name, self.title, **kwargs)
        self._build_ui()

    def _build_ui(self):
        vbox = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        scrwin = self.factory.create_scrolledwindow()
        self.app.add_widget('window-plugin-ui-manager-scrwin', scrwin)
        vbox.append(scrwin)
        pm = self.app.get_service('plugin-manager')
        view = self.app.add_widget('window-plugin-ui-manager-view', MiAZColumnViewPlugin(self.app))
        view.set_hexpand(True)
        view.set_vexpand(True)
        scrwin.set_child(view)

        # System Plugins
        items = []
        item_type = Plugin
        for plugin in pm.plugins:
            if pm.get_plugin_type(plugin) == MiAZPluginType.SYSTEM:
                pid = plugin.get_module_name()
                title = plugin.get_description()
                items.append(item_type(id=pid, title=title))
        view.update(items)
        return vbox

    # ~ def _create_widget_for_plugins(self):
        # ~ vbox = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        # ~ notebook = Gtk.Notebook()
        # ~ notebook.set_show_border(False)
        # ~ notebook.set_tab_pos(Gtk.PositionType.LEFT)
        # ~ widget = self._create_view_plugins_system()
        # ~ label = self.factory.create_notebook_label(icon_name='io.github.t00m.MiAZ-res-plugins-system', title='System')
        # ~ notebook.append_page(widget, label)
        # ~ widget = self._create_view_plugins_user()
        # ~ label = self.factory.create_notebook_label(icon_name='io.github.t00m.MiAZ-res-plugins', title='User')
        # ~ notebook.append_page(widget, label)
        # ~ vbox.append(notebook)
        # ~ return vbox

    # ~ def _create_view_plugins_system(self):
        # ~ vbox = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        # ~ scrwin = self.factory.create_scrolledwindow()
        # ~ self.app.add_widget('app-settings-plugins-system-scrwin', scrwin)
        # ~ vbox.append(scrwin)
        # ~ pm = self.app.get_service('plugin-manager')
        # ~ view = MiAZColumnViewPlugin(self.app)
        # ~ view.set_hexpand(True)
        # ~ view.set_vexpand(True)
        # ~ self.app.add_widget('app-settings-plugins-system-view', view)
        # ~ scrwin.set_child(view)

        # ~ # System Plugins
        # ~ items = []
        # ~ item_type = Plugin
        # ~ for plugin in pm.plugins:
            # ~ if pm.get_plugin_type(plugin) == MiAZPluginType.SYSTEM:
                # ~ pid = plugin.get_module_name()
                # ~ title = plugin.get_description()
                # ~ items.append(item_type(id=pid, title=title))
        # ~ view.update(items)
        # ~ return vbox

    # ~ def _create_view_plugins_user(self):
        # ~ vbox = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)

        # ~ # Add/Remove
        # ~ hbox = self.factory.create_box_horizontal(margin=0, spacing=0, hexpand=True, vexpand=False)
        # ~ hbox.get_style_context().add_class(class_name='toolbar')
        # ~ hbox.append(self.factory.create_button(icon_name='io.github.t00m.MiAZ-list-add-symbolic', title='Add plugin', callback=self._on_plugin_add))
        # ~ hbox.append(self.factory.create_button(icon_name='io.github.t00m.MiAZ-list-remove-symbolic', title='Remove plugin', callback=self._on_plugin_remove))
        # ~ vbox.append(hbox)

        # ~ # User Plugins
        # ~ scrwin = self.factory.create_scrolledwindow()
        # ~ self.app.add_widget('app-settings-plugins-user-scrwin', scrwin)
        # ~ vbox.append(scrwin)
        # ~ view = MiAZColumnViewPlugin(self.app)
        # ~ view.set_hexpand(True)
        # ~ view.set_vexpand(True)
        # ~ self.app.add_widget('app-settings-plugins-user-view', view)
        # ~ scrwin.set_child(view)
        # ~ self.update_user_plugins()
        # ~ return vbox
