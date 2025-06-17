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

from MiAZ.frontend.desktop.services.pluginsystem import MiAZPlugin

plugin_info = {
        'Module':        'viewitem',
        'Name':          'MiAZViewItem',
        'Loader':        'Python3',
        'Description':   _('Display document'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2025 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'http://github.com/t00m/MiAZ/README.adoc',
        'Version':       '0.6',
        'Category':      _('Visualisation and Diagrams'),
        'Subcategory':   _('Document Viewers')
    }


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
        self.plugin.register(self, plugin_info)

        ## Get logger
        self.log = self.plugin.get_logger()

        ## Get services
        self.actions = self.app.get_service('actions')
        self.factory = self.app.get_service('factory')

        ## Connect signals
        self.workspace = self.app.get_widget('workspace')
        self.workspace.connect('workspace-loaded', self.startup)
        self.workspace.connect('workspace-view-updated', self._on_selection_changed)
        view = self.app.get_widget('workspace-view')
        view.cv.connect("activate", self.document_display)
        selection = view.get_selection()
        selection.connect('selection-changed', self._on_selection_changed)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")

    def _on_selection_changed(self, *args):
        items = self.workspace.get_selected_items()
        button = self.app.get_widget('toolbar-top-button-view')
        if button is not None:
            visible = len(items) == 1
            button.set_visible(visible)

    def startup(self, *args):
        if not self.plugin.started():
            # Create menu item for plugin
            mnuItemName = self.plugin.get_menu_item_name()
            menuitem = self.factory.create_menuitem(name=mnuItemName, label=_('Display document'), callback=self.document_display)

            # Add plugin to its default (sub)category
            self.plugin.install_menu_entry(menuitem)

            # Button
            if self.app.get_widget('toolbar-top-button-view') is None:
                toolbar_top_right = self.app.get_widget('headerbar-right-box')
                button = self.factory.create_button(icon_name='io.github.t00m.MiAZ-view-document', tooltip=_('View document'), callback=self.document_display)
                button.set_visible(False)
                self.app.add_widget('toolbar-top-button-view', button)
                toolbar_top_right.append(button)

            # Plugin configured
            self.plugin.set_started(started=True)

    def document_display(self, *args):
        try:
            item = self.workspace.get_selected_items()[0]
            self.actions.document_display(item.id)
        except IndexError:
            self.log.debug("No item selected")
