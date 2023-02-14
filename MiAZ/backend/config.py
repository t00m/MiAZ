import os
import shutil

from gi.repository import GObject

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
# ~ from MiAZ.backend.util import json_load, json_save
from MiAZ.backend.models import MiAZModel, MiAZItem, File, Group, Person, Country, Purpose, Concept, SentBy, SentTo

class MiAZConfig(GObject.GObject):
    """ MiAZ Config class"""
    used = None
    default = None

    def __init__(self, backend, log, config_for, used=None, available=None, default=None, model=MiAZModel, must_copy=True, foreign=False):
        super().__init__()
        self.backend = backend
        self.util = self.backend.util
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
            items = self.util.json_load(filepath)
        except Exception as error:
            items = None
        return items

    def load_available(self) -> dict:
        return self.load(self.available)

    def load_used(self) -> dict:
        return self.load(self.used)

    def save_available(self, items: dict = {}) -> bool:
        return self.save(self.available, items)

    def save_used(self, items: dict = {}) -> bool:
        return self.save(self.used, items)

    def save_data(self, filepath: str = '', items: dict = {}) -> bool:
        if filepath == '':
            filepath = self.used
        try:
            self.util.json_save(filepath, items)
            saved = True
        except Exception as error:
            self.log.error(error)
            saved = False
        # ~ self.log.debug("Saved %s with %d items? %s", filepath, len(items), saved)
        return saved

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

    def exists_used(self, key: str) -> bool:
        config = self.load(self.used)
        if key in config:
            return True
        else:
            return False

    def exists_available(self, key: str) -> bool:
        config = self.load(self.available)
        if key in config:
            return True
        else:
            return False


    # ~ def exists(self, key: str) -> bool:
        # ~ found = False

        # ~ if self.must_copy:
            # ~ config = self.load(self.used)
        # ~ else:
            # ~ config = self.load(self.default)

        # ~ if isinstance(config, dict):
            # ~ try:
                # ~ if self.config_for == 'Extensions':
                    # ~ config[key.lower()]
                    # ~ found = True
                # ~ else:
                    # ~ config[key]
                    # ~ found = True
            # ~ except KeyError:
                # ~ found = False
        # ~ elif isinstance(config, list):
            # ~ if key.upper() in [item.upper() for item in config]:
                # ~ found = True
            # ~ else:
                # ~ found = False
        # ~ return found

    def add_available_batch(self, keysvalues: list):
        for key, value in keysvalues:
            self.add(self.available, key, value)

    def add_available(self, key: str, value: str = ''):
        self.add(self.available, key, value)

    def add_used(self, key: str, value: str = ''):
        self.add(self.used, key, value)

    def add(self, filepath: str, key: str, value:str  = ''):
        if len(key.strip()) == 0:
            return
        items = self.load(filepath)
        if not key in items:
            items[key] = value
            self.save(filepath, items=items)
            self.log.info("%s - Add: %s[%s] to %s", self.config_for, key, value, filepath)

    def remove_available_batch(self, keys:list):
        self.remove_batch(self.available, keys)

    def remove_used_batch(self, keys:list):
        self.remove_batch(self.used, keys)

    def remove_available(self, key:str):
        self.remove(self.available, key)

    def remove_used(self, key:str):
        self.remove(self.used, key)

    def remove_batch(self, filepath: str, keys: list):
        items = self.load(filepath)
        for key in keys:
            if key in items:
                del(items[key])
                self.log.info("%s - Remove: %s from %s", self.config_for, key, filepath)
        self.save(filepath=filepath, items=items)

    def remove(self, filepath: str, key: str):
        if key is None or key.strip() == '':
            return
        items = self.load(filepath)
        if key in items:
            del(items[key])
            self.save(filepath=filepath, items=items)
            self.log.info("%s - Remove: %s from %s", self.config_for, key, filepath)


class MiAZConfigApp(MiAZConfig):
    def __init__(self, backend):
        self.backend = backend
        self.util = self.backend.util
        GObject.GObject.__init__(self)
        GObject.signal_new('repo-settings-updated-app',
                            MiAZConfigApp,
                            GObject.SignalFlags.RUN_LAST, None, () )
        super().__init__(
            backend = backend,
            log=get_logger('MiAZ.Config.App'),
            config_for = 'App',
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

    def save(self, filepath: str = '', items: dict = {}) -> bool:
        if self.save_data(filepath, items):
            self.emit('repo-settings-updated-app')


class MiAZConfigCountries(MiAZConfig):
    def __init__(self, backend, dir_conf):
        sid_a = GObject.signal_lookup('repo-settings-updated-countries', MiAZConfigCountries)
        sid_u = GObject.signal_lookup('countries-used', MiAZConfigCountries)
        if sid_a == 0:
            GObject.GObject.__init__(self)
            GObject.signal_new('repo-settings-updated-countries',
                                MiAZConfigCountries,
                                GObject.SignalFlags.RUN_LAST, None, () )
        if sid_u == 0:
            GObject.GObject.__init__(self)
            GObject.signal_new('countries-used',
                                MiAZConfigCountries,
                                GObject.SignalFlags.RUN_LAST, None, () )
        super().__init__(
            backend = backend,
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

    def save(self, filepath: str = '', items: dict = {}) -> bool:
        saved = self.save_data(filepath, items)
        if saved:
            if filepath == self.available:
                self.emit('repo-settings-updated-countries')
            elif filepath == self.used:
                self.emit('countries-used')
        return saved

class MiAZConfigGroups(MiAZConfig):
    def __init__(self, backend, dir_conf):
        sid_a = GObject.signal_lookup('repo-settings-updated-groups-available', MiAZConfigGroups)
        sid_u = GObject.signal_lookup('groups-used', MiAZConfigGroups)
        if sid_a == 0:
            GObject.GObject.__init__(self)
            GObject.signal_new('repo-settings-updated-groups-available',
                                MiAZConfigGroups,
                                GObject.SignalFlags.RUN_LAST, None, () )
        if sid_u == 0:
            GObject.GObject.__init__(self)
            GObject.signal_new('groups-used',
                                MiAZConfigGroups,
                                GObject.SignalFlags.RUN_LAST, None, () )
        super().__init__(
            backend = backend,
            log=get_logger('MiAZ.Settings.Groups'),
            config_for = 'Groups',
            used = os.path.join(dir_conf, 'groups-used.json'),
            available = os.path.join(dir_conf, 'groups-available.json'),
            default = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-groups.json'),
            model = Group,
            must_copy = True
        )

    def save(self, filepath: str = '', items: dict = {}) -> bool:
        if self.save_data(filepath, items):
            if filepath == self.available:
                self.emit('repo-settings-updated-groups-available')
            elif filepath == self.used:
                self.emit('groups-used')

    def __repr__(self):
        return 'Group'

class MiAZConfigPurposes(MiAZConfig):
    def __init__(self, backend, dir_conf):
        sid = GObject.signal_lookup('repo-settings-updated-purposes', MiAZConfigPurposes)
        if sid == 0:
            GObject.GObject.__init__(self)
            GObject.signal_new('repo-settings-updated-purposes',
                                MiAZConfigPurposes,
                                GObject.SignalFlags.RUN_LAST, None, () )
        super().__init__(
            backend = backend,
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

    def save(self, filepath: str = '', items: dict = {}) -> bool:
        if self.save_data(filepath, items):
            self.emit('repo-settings-updated-purposes')

class MiAZConfigConcepts(MiAZConfig):
    def __init__(self, backend, dir_conf):
        sid = GObject.signal_lookup('repo-settings-updated-concepts', MiAZConfigConcepts)
        if sid == 0:
            GObject.GObject.__init__(self)
            GObject.signal_new('repo-settings-updated-concepts',
                                MiAZConfigConcepts,
                                GObject.SignalFlags.RUN_LAST, None, () )
        super().__init__(
            backend = backend,
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

    def save(self, filepath: str = '', items: dict = {}) -> bool:
        saved = self.save_data(filepath, items)
        if saved:
            self.emit('repo-settings-updated-concepts')
        return saved

class MiAZConfigPeople(MiAZConfig):
    def __init__(self, backend, dir_conf):
        sid_a = GObject.signal_lookup('repo-settings-updated-people', MiAZConfigPeople)
        sid_u = GObject.signal_lookup('repo-settings-updated-people-used', MiAZConfigPeople)
        if sid_a == 0:
            GObject.GObject.__init__(self)
            GObject.signal_new('repo-settings-updated-people',
                                MiAZConfigPeople,
                                GObject.SignalFlags.RUN_LAST, None, () )
        if sid_u == 0:
            GObject.GObject.__init__(self)
            GObject.signal_new('repo-settings-updated-people-used',
                                MiAZConfigPeople,
                                GObject.SignalFlags.RUN_LAST, None, () )
        super().__init__(
            backend = backend,
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

    def save(self, filepath: str = '', items: dict = {}) -> bool:
        saved = self.save_data(filepath, items)
        if saved:
            if filepath == self.available:
                self.emit('repo-settings-updated-people')
            elif filepath == self.used:
                self.emit('repo-settings-updated-people-used')
        return saved

class MiAZConfigSentBy(MiAZConfig):
    def __init__(self, backend, dir_conf):
        sid = GObject.signal_lookup('repo-settings-updated-sentby', MiAZConfigSentBy)
        if sid == 0:
            GObject.GObject.__init__(self)
            GObject.signal_new('repo-settings-updated-sentby',
                                MiAZConfigSentBy,
                                GObject.SignalFlags.RUN_LAST, None, () )
        super().__init__(
            backend = backend,
            log=get_logger('MiAZ.Settings.SentBy'),
            config_for = 'SentBy',
            used = os.path.join(dir_conf, 'sentby-used.json'),
            available = os.path.join(dir_conf, 'people-available.json'),
            default = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-people.json'),
            model = SentBy,
            must_copy = False
        )

    def __repr__(self):
        return 'SentBy'

    def save(self, filepath: str = '', items: dict = {}) -> bool:
        if self.save_data(filepath, items):
            self.emit('repo-settings-updated-sentby')

class MiAZConfigSentTo(MiAZConfig):
    def __init__(self, backend, dir_conf):
        self.backend = backend
        self.util = self.backend.util
        sid = GObject.signal_lookup('repo-settings-updated-sentto', MiAZConfigSentTo)
        if sid == 0:
            GObject.GObject.__init__(self)
            GObject.signal_new('repo-settings-updated-sentto',
                                MiAZConfigSentTo,
                                GObject.SignalFlags.RUN_LAST, None, () )
        super().__init__(
            backend = backend,
            log=get_logger('MiAZ.Settings.SentTo'),
            config_for = 'SentTo',
            used = os.path.join(dir_conf, 'sentto-used.json'),
            available = os.path.join(dir_conf, 'people-available.json'),
            default = os.path.join(ENV['GPATH']['RESOURCES'],
                            'MiAZ-people.json'),
            model = SentTo,
            must_copy = False
        )

    def __repr__(self):
        return 'SentTo'

    def save(self, filepath: str = '', items: dict = {}) -> bool:
        if self.save_data(filepath, items):
            self.emit('repo-settings-updated-sentto')
