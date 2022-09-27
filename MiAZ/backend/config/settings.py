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
            must_copy = False
        )

class MiAZConfigSettingsCountries(MiAZConfig):
    def __init__(self):
        super().__init__(
            log=get_logger('MiAZ.Settings.Countries'),
            config_for = 'Countries',
            config_local = ENV['FILE']['COUNTRIES'],
            config_global = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-countries.json'),
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
            must_copy = True
        )

class MiAZConfigSettingsOrganizations(MiAZConfig):
    def __init__(self):
        super().__init__(
            log=get_logger('MiAZ.Settings.Organizations'),
            config_for = 'Organizations',
            config_local = ENV['FILE']['ORGANIZATIONS'],
            config_global = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-organizations.json'),
            must_copy = False
        )

class MiAZConfigSettingsWho(MiAZConfig):
    def __init__(self):
        super().__init__(
            log=get_logger('MiAZ.Settings.Who'),
            config_for = 'Who',
            config_local = ENV['FILE']['WHO'],
            config_global = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-who.json'),
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
            must_copy = False
        )
