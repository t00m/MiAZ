import os
import shutil

from gi.repository import GObject

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.backend.util import json_load, json_save
from MiAZ.backend.models import MiAZModel, MiAZItem, File, Group, Subgroup, Person, Country, Purpose, Concept

class MiAZConfig(GObject.GObject):
    """ MiAZ Config class"""
    config_local = None
    config_global = None

    def __init__(self, log, config_for, config_local=None, config_available=None, config_global=None, config_model=MiAZModel, must_copy=True, foreign=False):
        super().__init__()
        self.log = log
        # ~ self.log.debug("Config dir: %s", config_local)
        self.config_for = config_for
        self.config_local = config_local
        self.config_available = config_available
        self.config_global = config_global
        self.config_model = config_model
        self.must_copy = must_copy
        self.foreign = foreign
        self.setup()

    def __repr__(self):
        return __class__.__name__

    def setup(self):
        self.log.debug("Setup configuration for %s", self.config_for)
        if not os.path.exists(self.config_available):
            self.log.debug("\t%s - Available configuration file doesn't exist", self.config_for)
            if self.config_global is not None:
                shutil.copy(self.config_global, self.config_available)
                self.log.debug("\t%s - Available config created: %s", self.config_for, os.path.basename(self.config_available))
            else:
                self.log.debug("\t%s - No global config available.", self.config_for)

            # ~ # Create empty local configuration
            # ~ self.save(items={})
            # ~ if self.must_copy:
                # ~ try:
                    # ~ self.log.debug("\t%s - Global config: (%s)", self.config_for, os.path.basename(self.config_global))
                    # ~ self.log.debug("\t%s - Available config: (%s)", self.config_for, os.path.basename(self.config_available))
                    # ~ self.log.debug("\t%s - Local config: (%s)", self.config_for, os.path.basename(self.config_local))
                    # ~ self.log.debug("\t%s - Global config copied to available", self.config_for)
                # ~ except (FileNotFoundError, IOError) as error:
                    # ~ self.log.error(error)
                    # ~ return None
            # ~ else:
                # ~ # Create an empty config file
                # ~ self.log.debug("\t%s - Creating empty config file", self.config_for)
                # ~ self.save(items={})

        # ~ if self.config_available is not None:
            # ~ if not os.path.exists(self.config_available):
                # ~ self.log.debug("\t%s - Creating empty available config file", self.config_for)
                # ~ self.save(filepath=self.config_available, items={})

        if not os.path.exists(self.config_local):
            self.log.debug("\t%s - Creating empty local config file", self.config_for)
            self.save(filepath=self.config_local, items={})

    def get_config_for(self):
        return self.config_for

    def get_config_local(self):
        return self.config_local

    def get_config_global(self):
        return self.config_global

    def get_config_foreign(self):
        return self.foreign

    def load(self, filepath:str) -> dict:
        try:
            adict = json_load(filepath)
        except Exception as error:
            adict = None
        return adict

    def save_data(self, filepath: str = '', items: dict = {}) -> bool:
        if filepath == '':
            filepath = self.config_local
        try:
            json_save(filepath, items)
            saved = True
        except Exception as error:
            self.log.error(error)
            saved = False
        self.log.debug("Saved %s with %d items? %s", filepath, len(items), saved)
        return saved

    def get(self, key: str) -> str:
        config = self.load(self.config_local)
        try:
            return config[key]
        except KeyError:
            return ''

    def set(self, key: str, value: str) -> None:
        items = self.load(self.config_local)
        items[key] = value
        self.save(items=items)

    def exists(self, key: str) -> bool:
        found = False

        if self.must_copy:
            config = self.load(self.config_local)
        else:
            config = self.load(self.config_global)

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
        items = self.load(self.config_local)
        if not key in items:
            items[key] = value.upper()
            self.save(items=items)
            self.log.info("%s - Add: %s[%s]", self.config_for, key, value)

    def remove(self, key):
        items = self.load(self.config_local)
        if key in items:
            del(items[key])
            self.save(items=items)
            self.log.info("%s - Remove: %s", self.config_for, key)


class MiAZConfigApp(MiAZConfig):
    def __init__(self):
        GObject.GObject.__init__(self)
        GObject.signal_new('repo-settings-updated-app',
                            MiAZConfigApp,
                            GObject.SignalFlags.RUN_LAST, None, () )
        super().__init__(
            log=get_logger('MiAZ.Config.App'),
            config_for = 'Miaz-application',
            config_available = ENV['FILE']['CONF'],
            config_local = ENV['FILE']['CONF'],
            config_global = None,
            must_copy = False
        )

    def exists(self, key: str) -> bool:
        config = self.load(self.config_local)
        if key in config:
            found = True
        else:
            found = False
        return found

    def save(self, filepath: str = '', items: dict = {}) -> bool:
        if self.save_data(filepath, items):
            self.emit('repo-settings-updated-app')


class MiAZConfigSettingsCountries(MiAZConfig):
    def __init__(self, dir_conf):
        GObject.GObject.__init__(self)
        GObject.signal_new('repo-settings-updated-countries',
                            MiAZConfigSettingsCountries,
                            GObject.SignalFlags.RUN_LAST, None, () )
        super().__init__(
            log=get_logger('MiAZ.Settings.Countries'),
            config_for = 'Countries',
            config_available = os.path.join(dir_conf, 'countries_all.json'),
            config_local = os.path.join(dir_conf, 'countries.json'),
            config_global = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-countries.json'),
            config_model = Country,
            must_copy = False,
            foreign = True
        )

    def save(self, filepath: str = '', items: dict = {}) -> bool:
        if self.save_data(filepath, items):
            self.emit('repo-settings-updated-countries')

class MiAZConfigSettingsGroups(MiAZConfig):
    def __init__(self, dir_conf):
        GObject.GObject.__init__(self)
        GObject.signal_new('repo-settings-updated-groups',
                            MiAZConfigSettingsGroups,
                            GObject.SignalFlags.RUN_LAST, None, () )
        super().__init__(
            log=get_logger('MiAZ.Settings.Groups'),
            config_for = 'Groups',
            config_local = os.path.join(dir_conf, 'groups.json'),
            config_available = os.path.join(dir_conf, 'groups_all.json'),
            config_global = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-groups.json'),
            config_model = Group,
            must_copy = True
        )

    def save(self, filepath: str = '', items: dict = {}) -> bool:
        if self.save_data(filepath, items):
            self.emit('repo-settings-updated-groups')

    def __repr__(self):
        return 'Group'

class MiAZConfigSettingsSubgroups(MiAZConfig):
    def __init__(self, dir_conf):
        GObject.GObject.__init__(self)
        GObject.signal_new('repo-settings-updated-subgroups',
                            MiAZConfigSettingsSubgroups,
                            GObject.SignalFlags.RUN_LAST, None, () )
        super().__init__(
            log=get_logger('MiAZ.Settings.Subgroups'),
            config_for = 'Subgroups',
            config_local = os.path.join(dir_conf, 'subgroups.json'),
            config_available = os.path.join(dir_conf, 'subgroups_all.json'),
            config_global = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-subgroups.json'),
            config_model = Subgroup,
            must_copy = True
        )

    def __repr__(self):
        return 'Subgroup'

    def save(self, filepath: str = '', items: dict = {}) -> bool:
        if self.save_data(filepath, items):
            self.emit('repo-settings-updated-subgroups')

class MiAZConfigSettingsPurposes(MiAZConfig):
    def __init__(self, dir_conf):
        GObject.GObject.__init__(self)
        GObject.signal_new('repo-settings-updated-purposes',
                            MiAZConfigSettingsPurposes,
                            GObject.SignalFlags.RUN_LAST, None, () )
        super().__init__(
            log=get_logger('MiAZ.Settings.Purposes'),
            config_for = 'Purposes',
            config_local = os.path.join(dir_conf, 'purposes.json'),
            config_available = os.path.join(dir_conf, 'purposes_all.json'),
            config_global = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-purposes.json'),
            config_model = Purpose,
            must_copy = True
        )

    def __repr__(self):
        return 'Purpose'

    def save(self, filepath: str = '', items: dict = {}) -> bool:
        if self.save_data(filepath, items):
            self.emit('repo-settings-updated-purposes')

class MiAZConfigSettingsConcepts(MiAZConfig):
    def __init__(self, dir_conf):
        GObject.GObject.__init__(self)
        GObject.signal_new('repo-settings-updated-concepts',
                            MiAZConfigSettingsConcepts,
                            GObject.SignalFlags.RUN_LAST, None, () )
        super().__init__(
            log=get_logger('MiAZ.Settings.Concepts'),
            config_for = 'Concepts',
            config_local = os.path.join(dir_conf, 'concepts.json'),
            config_available = os.path.join(dir_conf, 'concepts_all.json'),
            config_global = None,
            config_model = Concept,
            must_copy = False
        )

    def __repr__(self):
        return 'Concept'

    def save(self, filepath: str = '', items: dict = {}) -> bool:
        if self.save_data(filepath, items):
            self.emit('repo-settings-updated-concepts')

class MiAZConfigSettingsPeople(MiAZConfig):
    def __init__(self, dir_conf):
        sid = GObject.signal_lookup('repo-settings-updated-people', MiAZConfigSettingsPeople)
        if sid == 0:
            GObject.GObject.__init__(self)
            GObject.signal_new('repo-settings-updated-people',
                                MiAZConfigSettingsPeople,
                                GObject.SignalFlags.RUN_LAST, None, () )
        super().__init__(
            log=get_logger('MiAZ.Settings.People'),
            config_for = 'Person',
            config_local = os.path.join(dir_conf, 'people.json'),
            config_available = os.path.join(dir_conf, 'people_all.json'),
            config_global = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-people.json'),
            config_model = Person,
            must_copy = True
        )
        self.log.error("Signal ID: %d", sid)

    def __repr__(self):
        return 'Person'

    def save(self, filepath: str = '', items: dict = {}) -> bool:
        if self.save_data(filepath, items):
            self.emit('repo-settings-updated-people')
