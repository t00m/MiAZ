#!/usr/bin/env python
# -*- coding: utf-8 -*-

from MiAZ.frontend.desktop.widgets.configview import MiAZConfigView
from MiAZ.backend.config.settings import MiAZConfigSettingsExtensions

class MiAZExtensions(MiAZConfigView):
    """Class for managing Collections from Settings"""
    __gtype_name__ = 'MiAZExtensions'

    def __init__(self, app):
        super().__init__(app)
        self.config = MiAZConfigSettingsExtensions()

    def update(self):
        try:
            for extension in self.config.load():
                self.store.insert_with_values(-1, (0,), (extension,))
        except FileNotFoundError as error:
            self.log.error(error)
            return


