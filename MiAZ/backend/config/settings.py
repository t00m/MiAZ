#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.backend.config import MiAZConfig

class MiAZConfigApp(MiAZConfig):
    def __init__(self):
        super().__init__(
            log=get_logger('MiAZ.Config.App'),
            config_for = 'Miaz-application',
            config_local = ENV['FILE']['CONF'],
            config_global = None,
            config_is = dict,
            must_copy = False
        )

    def exists(self, key: str) -> bool:
        config = self.load()
        if key in config:
            found = True
        else:
            found = False
        return found

class MiAZConfigSettingsCountries(MiAZConfig):
    def __init__(self):
        super().__init__(
            log=get_logger('MiAZ.Settings.Countries'),
            config_for = 'Countries',
            config_local = ENV['FILE']['COUNTRIES'],
            config_global = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-countries.json'),
            config_is = dict,
            must_copy = False
        )

class MiAZConfigSettingsLanguages(MiAZConfig):
    def __init__(self):
        super().__init__(
            log=get_logger('MiAZ.Settings.Languages'),
            config_for = 'Languages',
            config_local = ENV['FILE']['LANGUAGES'],
            config_global = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-languages.json'),
            config_is = dict,
            must_copy = False
        )

class MiAZConfigSettingsCollections(MiAZConfig):
    def __init__(self):
        super().__init__(
            log=get_logger('MiAZ.Settings.Collections'),
            config_for = 'Collections',
            config_local = ENV['FILE']['COLLECTIONS'],
            config_global = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-collections.json'),
            config_is = list,
            must_copy = True
        )

class MiAZConfigSettingsPurposes(MiAZConfig):
    def __init__(self):
        super().__init__(
            log=get_logger('MiAZ.Settings.Purposes'),
            config_for = 'Purposes',
            config_local = ENV['FILE']['PURPOSES'],
            config_global = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-purposes.json'),
            config_is = list,
            must_copy = True
        )

class MiAZConfigSettingsConcepts(MiAZConfig):
    def __init__(self):
        super().__init__(
            log=get_logger('MiAZ.Settings.Concepts'),
            config_for = 'Concepts',
            config_local = ENV['FILE']['CONCEPTS'],
            config_global = None,
            config_is = list,
            must_copy = False
        )

class MiAZConfigSettingsOrganizations(MiAZConfig):
    def __init__(self):
        super().__init__(
            log=get_logger('MiAZ.Settings.Organizations'),
            config_for = 'Organizations',
            config_local = ENV['FILE']['ORGANIZATIONS'],
            config_global = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-organizations.json'),
            config_is = dict,
            must_copy = True
        )

class MiAZConfigSettingsExtensions(MiAZConfig):
    def __init__(self):
        super().__init__(
            log=get_logger('MiAZ.Settings.Extensions'),
            config_for = 'Extensions',
            config_local = ENV['FILE']['EXTENSIONS'],
            config_global = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-extensions.json'),
            config_is = dict,
            must_copy = False
        )

    def get_sections(self):
        sections = set()
        extensions = self.load_global()
        for ext in extensions:
            esections = extensions[ext]
            for section in esections:
                sections.add(section)
        return sections
