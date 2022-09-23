#!/usr/bin/env python
# -*- coding: utf-8 -*-

from MiAZ.frontend.desktop.widgets.configview import MiAZConfigView


class MiAZCollections(MiAZConfigView):
    """Class for managing Collections from Settings"""
    __gtype_name__ = 'MiAZCollections'
    current = None

    def __init__(self, app):
        super().__init__(app)

    def update(self):
        if self.config_local is None:
            return

        # Check config file and create it if doesn't exist
        self.config_check()

        self.store.clear()
        items = self.config_load()
        pos = 0
        for item in items:
            node = self.store.insert_with_values(pos, (0,), (item,))
            pos += 1