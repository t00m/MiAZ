#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: __init__.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Backend Package initialization
"""

import os

import gi
from gi.repository import GObject

from MiAZ.backend.log import get_logger
from MiAZ.backend.config import MiAZConfigApp
from MiAZ.backend.util import MiAZUtil
from MiAZ.backend.stats import MiAZStats
from MiAZ.backend.repository import MiAZRepository
from MiAZ.backend.config import MiAZConfigRepositories


class MiAZBackend(GObject.GObject):
    """Backend class"""
    __gtype_name__ = 'MiAZBackend'
    _config = {} # Dictionary holding configurations

    def __init__(self, app) -> None:
        GObject.GObject.__init__(self)
        self.app = app
        self.log = get_logger('MiAZBackend')
        self.app.add_service('repo', MiAZRepository(self))
        self.app.add_service('util', MiAZUtil(self))
        self.app.add_service('stats', MiAZStats(self))
        self._config['App'] = MiAZConfigApp(self)
        self._config['Repository'] = MiAZConfigRepositories(self)

    def get_config(self):
        return self._config

    def get_service(self, service: str):
        """Convenient method to get a service"""
        return self.app.get_service(service)

    def add_service(self, name: str, service: GObject.GObject) -> GObject.GObject:
        """Convenient method to get a service"""
        return self.app.add_service(name, service)
