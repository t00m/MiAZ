import os
import shutil

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.backend.util import json_load, json_save
from MiAZ.backend.models import MiAZModel, File, Group, Subgroup, Person, Country, Purpose, Concept

class MiAZConfig():
    """ MiAZ Config class"""
    config_local = None
    config_global = None

    def __init__(self, log, config_for, config_local=None, config_global=None, config_is=dict, config_model=MiAZModel, must_copy=True, foreign=False):
        super().__init__()
        self.log = log
        self.config_for = config_for
        self.config_local = config_local
        self.config_global = config_global
        self.config_is = config_is
        self.config_model = config_model
        self.must_copy = must_copy
        self.foreign = foreign
        self.setup()

    def __repr__(self):
        return __class__.__name__

    def setup(self):
        if not os.path.exists(self.config_local):
            self.log.debug("%s - Local configuration file doesn't exist", self.config_for)
            if self.must_copy:
                try:
                    shutil.copy(self.config_global, self.config_local)
                    self.log.debug("%s - Global config: (%s)", self.config_for, self.config_global)
                    self.log.debug("%s - Local config: (%s)", self.config_for, self.config_local)
                    self.log.debug("%s - Global config copied to local", self.config_for)
                except (FileNotFoundError, IOError) as error:
                    self.log.error(error)
                    return None
            else:
                # Create an empty config file
                self.log.debug("%s - Creating empty config file", self.config_for)
                if self.config_is is dict:
                    self.save({})
                else:
                    self.save([])

    def get_config_for(self):
        return self.config_for

    def get_config_local(self):
        return self.config_local

    def get_config_global(self):
        return self.config_global

    def get_config_is(self):
        return self.config_is

    def get_config_foreign(self):
        return self.foreign

    def load(self) -> dict:
        try:
            config = json_load(self.config_local)
        except Exception as error:
            config = None
            self.log.error(error)
        return config

    def load_global(self) -> dict:
        try:
            items = json_load(self.config_global)
        except Exception as error:
            items = None
        return items

    def save(self, items: dict) -> bool:
        try:
            json_save(self.config_local, items)
            self.log.debug("%s - Local config file saved", self.config_for)
            saved = True
        except Exception as error:
            self.log.error(error)
            saved = False
        return saved

    def get(self, key: str) -> str:
        config = self.load()
        try:
            return config[key]
        except KeyError:
            return ''

    def set(self, key: str, value: str) -> None:
        config = self.load()
        config[key] = value
        self.save(config)

    def exists(self, key: str) -> bool:
        found = False

        if self.must_copy:
            config = self.load()
        else:
            config = self.load_global()

        if isinstance(config, dict):
            try:
                if self.config_for == 'Extensions':
                    config[key.lower()]
                    found = True
                else:
                    config[key.upper()]
                    found = True
            except KeyError:
                found = False
        elif isinstance(config, list):
            if key.upper() in [item.upper() for item in config]:
                found = True
            else:
                found = False
        return found

    def add(self, key, value=None):
        if self.config_is is dict:
            self.dict_add(key, value)
        else:
            self.list_add(key)

    def remove(self, key):
        if self.config_is is dict:
            self.dict_remove(key)
        else:
            self.list_remove(key)

    def list_add(self, key):
        config = self.load()
        if not key in config:
            config.append(key.upper())
            self.save(sorted(config))
            self.log.info("%s - Add: %s", self.config_for, key)

    def list_remove(self, key):
        config = self.load()
        if key in config:
            config.remove(key)
            self.save(config)
            self.log.info("%s - Remove: %s", self.config_for, key)

    def dict_add(self, key, value):
        config = self.load()
        if not key in config:
            config[key] = value.upper()
            self.save(config)
            self.log.info("%s - Add: %s[%s]", self.config_for, key, value)

    def dict_remove(self, key):
        config = self.load()
        if key in config:
            del(config[key])
            self.save(config)
            self.log.info("%s - Remove: %s", self.config_for, key)


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
            config_model = Country,
            must_copy = False,
            foreign = True
        )

class MiAZConfigSettingsGroups(MiAZConfig):
    def __init__(self):
        super().__init__(
            log=get_logger('MiAZ.Settings.Groups'),
            config_for = 'Groups',
            config_local = ENV['FILE']['GROUPS'],
            config_global = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-groups.json'),
            config_is = list,
            config_model = Group,
            must_copy = True
        )

    def __repr__(self):
        return 'Group'

class MiAZConfigSettingsSubgroups(MiAZConfig):
    def __init__(self):
        super().__init__(
            log=get_logger('MiAZ.Settings.Subgroups'),
            config_for = 'Subgroups',
            config_local = ENV['FILE']['SUBGROUPS'],
            config_global = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-subgroups.json'),
            config_is = list,
            config_model = Subgroup,
            must_copy = True
        )

    def __repr__(self):
        return 'Subgroup'

class MiAZConfigSettingsPurposes(MiAZConfig):
    def __init__(self):
        super().__init__(
            log=get_logger('MiAZ.Settings.Purposes'),
            config_for = 'Purposes',
            config_local = ENV['FILE']['PURPOSES'],
            config_global = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-purposes.json'),
            config_is = list,
            config_model = Purpose,
            must_copy = True
        )

    def __repr__(self):
        return 'Purpose'

class MiAZConfigSettingsConcepts(MiAZConfig):
    def __init__(self):
        super().__init__(
            log=get_logger('MiAZ.Settings.Concepts'),
            config_for = 'Concepts',
            config_local = ENV['FILE']['CONCEPTS'],
            config_global = None,
            config_is = list,
            config_model = Concept,
            must_copy = False
        )

    def __repr__(self):
        return 'Concept'

class MiAZConfigSettingsPerson(MiAZConfig):
    def __init__(self):
        super().__init__(
            log=get_logger('MiAZ.Settings.Organizations'),
            config_for = 'Person',
            config_local = ENV['FILE']['PERSONS'],
            config_global = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-persons.json'),
            config_is = dict,
            config_model = Person,
            must_copy = True
        )

    def __repr__(self):
        return 'Person'
