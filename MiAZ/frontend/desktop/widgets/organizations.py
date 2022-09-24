#!/usr/bin/env python
# -*- coding: utf-8 -*-

from MiAZ.frontend.desktop.widgets.configview import MiAZConfigView
from MiAZ.backend.config.settings import MiAZConfigSettingsOrganizations

class MiAZOrganizations(MiAZConfigView):
    """Class for managing Organizations from Settings"""
    __gtype_name__ = 'MiAZOrganizations'

    def __init__(self, app):
        super().__init__(app)
        self.config = MiAZConfigSettingsOrganizations()

    def update(self):
        try:
            for organization in self.config.load():
                self.store.insert_with_values(-1, (0,), (organization,))
        except FileNotFoundError as error:
            self.log.error(error)
            return