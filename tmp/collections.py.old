#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gi.repository import Gtk

from MiAZ.backend.log import get_logger
from MiAZ.frontend.desktop.widgets.configview import MiAZConfigView
from MiAZ.frontend.desktop.widgets.dialogs import MiAZDialogAdd

from MiAZ.backend.config import MiAZConfigSettingsCollections

class MiAZCollections(MiAZConfigView):
    """Class for managing Collections from Settings"""
    __gtype_name__ = 'MiAZCollections'
    current = None

    def __init__(self, app):
        self.config = MiAZConfigSettingsCollections()
        config_for = self.config.get_config_for()
        super().__init__(app, config_for)
        self.log = get_logger('MiAZSettings-%s' % config_for)

    def update(self):
        self.store.clear()
        for item in self.config.load():
            node = self.store.insert_with_values(-1, (0,), (item,))
