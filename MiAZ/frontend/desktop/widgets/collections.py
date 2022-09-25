#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gi.repository import Gtk

from MiAZ.frontend.desktop.widgets.configview import MiAZConfigView
from MiAZ.backend.config.settings import MiAZConfigSettingsCollections
from MiAZ.frontend.desktop.widgets.dialogs import MiAZDialogAdd


class MiAZCollections(MiAZConfigView):
    """Class for managing Collections from Settings"""
    __gtype_name__ = 'MiAZCollections'
    current = None

    def __init__(self, app):
        super().__init__(app)
        self.config = MiAZConfigSettingsCollections()

    def update(self):
        self.store.clear()
        for item in self.config.load():
            node = self.store.insert_with_values(-1, (0,), (item,))

    def on_item_add(self, *args):
        dialog = MiAZDialogAdd(self.app, self.get_root(), 'Add a new collection', 'Collection name', '')
        boxkey2 = dialog.get_boxKey2()
        boxkey2.set_visible(False)
        dialog.connect('response', self.on_response_item_add)
        dialog.show()

    def on_response_item_add(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            value = dialog.get_value1()
            if len(value) > 0:
                items = self.config.load()
                if not value in items:
                    items.append(value.upper())
                    self.config.save(items)
                    self.update()
        dialog.destroy()