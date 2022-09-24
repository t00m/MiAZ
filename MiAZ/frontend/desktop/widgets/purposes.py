#!/usr/bin/env python
# -*- coding: utf-8 -*-

from MiAZ.frontend.desktop.widgets.configview import MiAZConfigView
from MiAZ.backend.config.settings import MiAZConfigSettingsPurposes


class MiAZPurposes(MiAZConfigView):
    """Class for managing Purposes from Settings"""
    __gtype_name__ = 'MiAZPurposes'

    def __init__(self, app):
        super().__init__(app)
        self.config = MiAZConfigSettingsPurposes()

    def update(self):
        self.store.clear()
        for item in self.config.load():
            node = self.store.insert_with_values(-1, (0,), (item,))
