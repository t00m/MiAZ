import os
import shutil

from gi.repository import GObject

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.backend.util import json_load, json_save
from MiAZ.backend.models import MiAZModel, MiAZItem, File, Group, Subgroup, Person, Country, Purpose, Concept, SentBy, SentTo

class MiAZConfig(GObject.GObject):
    """ MiAZ Config class"""
    used = None
    default = None

    def __init__(self, log, config_for, used=None, available=None, default=None, model=MiAZModel, must_copy=True, foreign=False):
        super().__init__()
        self.log = log
        self.config_for = config_for
        self.used = used
        self.available = available
        self.default = default
        self.model = model
        self.must_copy = must_copy
        self.foreign = foreign
        self.setup()

    def __repr__(self):
        return __class__.__name__

    def setup(self):
        if not os.path.exists(self.available):
            if self.default is not None:
                shutil.copy(self.default, self.available)
                self.log.debug("%s - Available configuration created from default", self.config_for)
            else:
                self.save(filepath=self.available, items={})
                self.log.debug("%s - Available configuration file created (empty)", self.config_for)

        if not os.path.exists(self.used):
            self.save(filepath=self.used, items={})
            self.log.debug("%s - Used configuration file created (empty)", self.config_for)

    def get_config_for(self):
        return self.config_for

    def get_used(self):
        return self.used

    def get_default(self):
        return self.default

    def get_config_foreign(self):
        return self.foreign

    def load(self, filepath:str) -> dict:
        try:
            adict = json_load(filepath)
        except Exception as error:
            adict = None
        return adict

    def save_data(self, filepath: str, items: dict) -> bool:
        try:
            json_save(filepath, items)
            self.log.debug("%s - Saved %d items in %s", self.config_for, len(items), filepath)
        except Exception as error:
            self.log.error(error)
            raise

    def get(self, key: str) -> str:
        config = self.load(self.used)
        try:
            return config[key]
        except KeyError:
            return ''

    def set(self, key: str, value: str) -> None:
        items = self.load(self.used)
        items[key] = value
        self.save(items=items)

    def exists(self, key: str) -> bool:
        found = False

        if self.must_copy:
            config = self.load(self.used)
        else:
            config = self.load(self.default)

        try:
            config[key]
            found = True
        except KeyError:
            found = False

        return found

    def add(self, filepath: str, key: str, value: str):
        if len(key.strip()) == 0:
            return
        if len(filepath) == 0:
            filepath = self.available

        items = self.load(filepath)
        if not key in items:
            key = key.replace('-', '_')
            items[key] = value
            self.save(filepath=filepath, items=items)
            self.log.info("%s - Add: %s[%s] to %s", self.config_for, key, value, filepath)

    def remove(self, filepath: str, key: str):
        if key is None:
            return
        if len(key) == 0:
            return

        if filepath is None:
            return
        if len(filepath) == 0:
            filepath = self.available

        items = self.load(filepath)
        if key in items:
            del(items[key])
            self.save(filepath=filepath, items=items)
            self.log.info("%s - Remove: %s from: %s", self.config_for, key, filepath)


class MiAZConfigApp(MiAZConfig):
    def __init__(self):
        GObject.GObject.__init__(self)
        GObject.signal_new('repo-settings-updated-app',
                            MiAZConfigApp,
                            GObject.SignalFlags.RUN_LAST, None, () )
        super().__init__(
            log=get_logger('MiAZ.Config.App'),
            config_for = 'Miaz-application',
            available = ENV['FILE']['CONF'],
            used = ENV['FILE']['CONF'],
            default = None,
            must_copy = False
        )

    def exists(self, key: str) -> bool:
        config = self.load(self.used)
        if key in config:
            found = True
        else:
            found = False
        return found

    def save(self, filepath: str, items: dict) -> bool:
        if self.save_data(filepath, items):
            self.emit('repo-settings-updated-app')


class MiAZConfigSettingsCountries(MiAZConfig):
    def __init__(self, dir_conf):
        sid = GObject.signal_lookup('repo-settings-updated-countries', MiAZConfigSettingsCountries)
        if sid == 0:
            GObject.GObject.__init__(self)
            GObject.signal_new('repo-settings-updated-countries',
                                MiAZConfigSettingsCountries,
                                GObject.SignalFlags.RUN_LAST, None, () )
        super().__init__(
            log=get_logger('MiAZ.Settings.Countries'),
            config_for = 'Countries',
            available = os.path.join(dir_conf, 'countries-available.json'),
            used = os.path.join(dir_conf, 'countries-used.json'),
            default = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-countries.json'),
            model = Country,
            must_copy = False,
            foreign = True
        )

    def save(self, filepath: str, items: dict) -> bool:
        if self.save_data(filepath, items):
            self.emit('repo-settings-updated-countries')

class MiAZConfigSettingsGroups(MiAZConfig):
    def __init__(self, dir_conf):
        sid = GObject.signal_lookup('repo-settings-updated-groups', MiAZConfigSettingsGroups)
        if sid == 0:
            GObject.GObject.__init__(self)
            GObject.signal_new('repo-settings-updated-groups',
                                MiAZConfigSettingsGroups,
                                GObject.SignalFlags.RUN_LAST, None, () )
        super().__init__(
            log=get_logger('MiAZ.Settings.Groups'),
            config_for = 'Groups',
            used = os.path.join(dir_conf, 'groups-used.json'),
            available = os.path.join(dir_conf, 'groups-available.json'),
            default = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-groups.json'),
            model = Group,
            must_copy = True
        )

    def save(self, filepath: str, items: dict) -> bool:
        if self.save_data(filepath, items):
            self.emit('repo-settings-updated-groups')

    def __repr__(self):
        return 'Group'

class MiAZConfigSettingsSubgroups(MiAZConfig):
    def __init__(self, dir_conf):
        sid = GObject.signal_lookup('repo-settings-updated-subgroups', MiAZConfigSettingsSubgroups)
        if sid == 0:
            GObject.GObject.__init__(self)
            GObject.signal_new('repo-settings-updated-subgroups',
                                MiAZConfigSettingsSubgroups,
                                GObject.SignalFlags.RUN_LAST, None, () )
        super().__init__(
            log=get_logger('MiAZ.Settings.Subgroups'),
            config_for = 'Subgroups',
            used = os.path.join(dir_conf, 'subgroups-used.json'),
            available = os.path.join(dir_conf, 'subgroups-available.json'),
            default = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-subgroups.json'),
            model = Subgroup,
            must_copy = True
        )

    def __repr__(self):
        return 'Subgroup'

    def save(self, filepath: str, items: dict) -> bool:
        if self.save_data(filepath, items):
            self.emit('repo-settings-updated-subgroups')

class MiAZConfigSettingsPurposes(MiAZConfig):
    def __init__(self, dir_conf):
        sid = GObject.signal_lookup('repo-settings-updated-purposes', MiAZConfigSettingsPurposes)
        if sid == 0:
            GObject.GObject.__init__(self)
            GObject.signal_new('repo-settings-updated-purposes',
                                MiAZConfigSettingsPurposes,
                                GObject.SignalFlags.RUN_LAST, None, () )
        super().__init__(
            log=get_logger('MiAZ.Settings.Purposes'),
            config_for = 'Purposes',
            used = os.path.join(dir_conf, 'purposes-used.json'),
            available = os.path.join(dir_conf, 'purposes-available.json'),
            default = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-purposes.json'),
            model = Purpose,
            must_copy = True
        )

    def __repr__(self):
        return 'Purpose'

    def save(self, filepath: str, items: dict) -> bool:
        if self.save_data(filepath, items):
            self.emit('repo-settings-updated-purposes')

class MiAZConfigSettingsConcepts(MiAZConfig):
    def __init__(self, dir_conf):
        sid = GObject.signal_lookup('repo-settings-updated-concepts', MiAZConfigSettingsConcepts)
        if sid == 0:
            GObject.GObject.__init__(self)
            GObject.signal_new('repo-settings-updated-concepts',
                                MiAZConfigSettingsConcepts,
                                GObject.SignalFlags.RUN_LAST, None, () )
        super().__init__(
            log=get_logger('MiAZ.Settings.Concepts'),
            config_for = 'Concepts',
            used = os.path.join(dir_conf, 'concepts-used.json'),
            available = os.path.join(dir_conf, 'concepts-available.json'),
            default = None,
            model = Concept,
            must_copy = False
        )

    def __repr__(self):
        return 'Concept'

    def save(self, filepath: str, items: dict) -> bool:
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
            used = os.path.join(dir_conf, 'people-used.json'),
            available = os.path.join(dir_conf, 'people-available.json'),
            default = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-people.json'),
            model = Person,
            must_copy = True
        )

    def __repr__(self):
        return 'Person'

    def save(self, filepath: str, items: dict) -> bool:
        if self.save_data(filepath, items):
            self.emit('repo-settings-updated-people')

class MiAZConfigSettingsSentBy(MiAZConfig):
    def __init__(self, dir_conf):
        sid = GObject.signal_lookup('repo-settings-updated-sentby', MiAZConfigSettingsSentBy)
        if sid == 0:
            GObject.GObject.__init__(self)
            GObject.signal_new('repo-settings-updated-sentby',
                                MiAZConfigSettingsSentBy,
                                GObject.SignalFlags.RUN_LAST, None, () )
        super().__init__(
            log=get_logger('MiAZ.Settings.SentBy'),
            config_for = 'SentBy',
            used = os.path.join(dir_conf, 'people-used.json'),
            available = os.path.join(dir_conf, 'people-available.json'),
            default = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-people.json'),
            model = SentBy,
            must_copy = False
        )

    def __repr__(self):
        return 'SentBy'

    def save(self, filepath: str, items: dict) -> bool:
        if self.save_data(filepath, items):
            self.emit('repo-settings-updated-sentby')

class MiAZConfigSettingsSentTo(MiAZConfig):
    def __init__(self, dir_conf):
        sid = GObject.signal_lookup('repo-settings-updated-sentto', MiAZConfigSettingsSentTo)
        if sid == 0:
            GObject.GObject.__init__(self)
            GObject.signal_new('repo-settings-updated-sentto',
                                MiAZConfigSettingsSentTo,
                                GObject.SignalFlags.RUN_LAST, None, () )
        super().__init__(
            log=get_logger('MiAZ.Settings.SentTo'),
            config_for = 'SentTo',
            used = os.path.join(dir_conf, 'people-used.json'),
            available = os.path.join(dir_conf, 'people-available.json'),
            default = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-people.json'),
            model = SentTo,
            must_copy = False
        )

    def __repr__(self):
        return 'SentTo'

    def save(self, filepath: str, items: dict) -> bool:
        if self.save_data(filepath, items):
            self.emit('repo-settings-updated-sentto')
