#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: export2csv.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items to CSV
"""

from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Peas

from MiAZ.backend.pluginsystem import MiAZPlugin


class MiAZToolbarViewItemPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZToolbarViewItemPlugin'
    object = GObject.Property(type=GObject.Object)
    plugin = None
    file = __file__.replace('.py', '.plugin')

    def do_activate(self):
        """Plugin activation"""
        # Setup plugin
        ## Get pointer to app
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)

        ## Initialize plugin
        self.plugin.register(self.file)

        ## Get logger
        self.log = self.plugin.get_logger()

        workspace = self.app.get_widget('workspace')
        workspace.connect('workspace-loaded', self.startup)
        workspace.connect('workspace-view-updated', self._on_selection_changed)
        view = self.app.get_widget('workspace-view')
        view.cv.connect("activate", self.callback)
        selection = view.get_selection()
        selection.connect('selection-changed', self._on_selection_changed)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")

    def _on_selection_changed(self, *args):
        workspace = self.app.get_widget('workspace')
        items = workspace.get_selected_items()
        button = self.app.get_widget('toolbar-top-button-view')
        if button is not None:
            visible = len(items) == 1
            button.set_visible(visible)

    def startup(self, *args):
        if not self.plugin.menu_item_loaded():
            # Create menu item for plugin
            menuitem = self.plugin.get_menu_item(callback=None)

            # Add plugin to its default (sub)category
            self.plugin.install_menu_entry(menuitem)

            # Button
            if self.app.get_widget('toolbar-top-button-view') is None:
                factory = self.app.get_service('factory')
                toolbar_top_right = self.app.get_widget('headerbar-right-box')
                button = factory.create_button(icon_name='io.github.t00m.MiAZ-view-document', tooltip=_('View document'), callback=self.callback)
                button.set_visible(False)
                self.app.add_widget('toolbar-top-button-view', button)
                toolbar_top_right.append(button)

    def callback(self, *args):
        try:
            workspace = self.app.get_widget('workspace')
            item = workspace.get_selected_items()[0]
            actions = self.app.get_service('actions')
            actions.document_display(item.id)
        except IndexError:
            self.log.debug("No item selected")
