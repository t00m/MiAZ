#!/usr/bin/python3

"""
# File: config.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: App configuration
"""

import os
import shutil

from gi.repository import GObject

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import MiAZModel, Group, Person, Country, Purpose, Concept, SentBy, SentTo, Project, Repository, Plugin

class MiAZConfig(GObject.GObject):
    """ MiAZ Config class"""
    used = None
    default = None
    cache = {}

    def __init__(self, app, log, config_for, used=None, available=None, default=None, model=MiAZModel, must_copy=True, foreign=False):
        super().__init__()
        self.app = app
        self.util = self.app.get_service('util')
        self.log = log
        self.config_for = config_for
        self.used = used
        self.available = available
        self.default = default
        self.model = model
        self.must_copy = must_copy
        self.foreign = foreign
        self.setup()

        sid_a = GObject.signal_lookup('available-updated', MiAZConfig)
        sid_u = GObject.signal_lookup('used-updated', MiAZConfig)
        if sid_a == 0:
            GObject.GObject.__init__(self)
            GObject.signal_new('available-updated',
                                MiAZConfig,
                                GObject.SignalFlags.RUN_LAST, None, () )
        if sid_u == 0:
            GObject.GObject.__init__(self)
            GObject.signal_new('used-updated',
                                MiAZConfig,
                                GObject.SignalFlags.RUN_LAST, None, () )
        self.log.debug("Config for %s initialited", self.config_for)

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
            config_changed = self.cache[filepath]['changed']
        except KeyError:
            config_changed = True

        if config_changed:
            # ~ self.log.debug("Loading from %s", filepath)
            try:
                items = self.util.json_load(filepath)
                self.cache[filepath] = {}
                self.cache[filepath]['changed'] = False
                self.cache[filepath]['items'] = items
                # ~ self.log.debug("In-memory config data updated for '%s'", filepath)
            except Exception:
                items = None
            return items
        else:
            # ~ self.log.debug("Got %s items from cache for %s", self.config_for, filepath)
            self.cache[filepath]['changed'] = False
            return self.cache[filepath]['items']

    def load_available(self) -> dict:
        # ~ self.log.debug("%s available: %s", self.config_for, self.available)
        return self.load(self.available)

    def load_used(self) -> dict:
        # ~ self.log.debug("%s used: %s", self.config_for, self.used)
        return self.load(self.used)

    def save(self, filepath: str = '', items: dict = {}) -> bool:
        saved = self.save_data(filepath, items)
        if saved:
            if filepath == self.available:
                self.emit('available-updated')
            elif filepath == self.used:
                self.emit('used-updated')
            try:
                self.cache[filepath]['changed'] = True
            except KeyError:
                self.cache[filepath] = {}
                self.cache[filepath]['changed'] = True
            # ~ self.log.debug("Cache update for '%s'", filepath)
        return saved

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
        return saved

    def get(self, key: str) -> str:
        config = self.load(self.used)
        try:
            # return description, if it exists
            return config[key]
        except KeyError:
            if key in config:
                # otherwise, return the key
                return key
            else:
                # if no key (and no description) return None
                return None

    def set(self, key: str, value: str) -> None:
        items = self.load(self.used)
        items[key] = value
        return self.save(items=items)

    def exists_used(self, key: str) -> bool:
        config = self.load(self.used)
        return key in config

    def exists_available(self, key: str) -> bool:
        config = self.load(self.available)
        return key in config

    def add_available_batch(self, keysvalues: list):
        filepath = self.available
        items = self.load(filepath)
        saved = 0
        for key, value in keysvalues:
            if len(key.strip()) != 0:
                # ~ if key not in items:
                key = self.util.valid_key(key)
                items[key] = value
                saved += 1
        if saved > 0:
            self.save(filepath, items=items)
            self.log.info("%s - Added %d keys to %s", self.config_for, saved, filepath)

    def add_available(self, key: str, value: str = ''):
        self.add(self.available, key, value)

    def add_used_batch(self, keysvalues: list):
        filepath = self.used
        items = self.load(filepath)
        saved = 0
        for key, value in keysvalues:
            if len(key.strip()) != 0:
                # ~ if key not in items:
                key = self.util.valid_key(key)
                items[key] = value
                saved += 1
        if saved > 0:
            self.save(filepath, items=items)
            self.log.info("%s - Added %d keys to %s", self.config_for, saved, filepath)

    def add_used(self, key: str, value: str = '') -> bool:
        return self.add(self.used, key, value)

    def add(self, filepath: str, key: str, value:str  = '') -> bool:
        added = True
        if len(key.strip()) == 0:
            self.log.warning('Key is None or empty. Add skipped')
        items = self.load(filepath)
        if key not in items:
            key = self.util.valid_key(key)
            items[key] = value
            self.save(filepath, items=items)
            self.log.info("%s - Add: %s[%s] to %s", self.config_for, key, value, filepath)
            added = True
        return added

    def remove_available_batch(self, keys:list):
        self.remove_batch(self.available, keys)

    def remove_used_batch(self, keys:list):
        self.remove_batch(self.used, keys)

    def remove_available(self, key:str):
        self.remove(self.available, key)

    def remove_used(self, key:str) -> bool:
        return self.remove(self.used, key)

    def remove_batch(self, filepath: str, keys: list):
        # FIXME: check del operation
        items = self.load(filepath)
        for key in keys:
            if key in items:
                del items[key]
                self.log.info("%s - Remove: %s from %s", self.config_for, key, filepath)
        self.save(filepath=filepath, items=items)

    def remove(self, filepath: str, key: str) -> bool:
        # FIXME: check del operation
        removed = False
        if key is None or key.strip() == '':
            self.log.warning('Key is None or empty. Remove skipped')
        items = self.load(filepath)
        if key in items:
            del items[key]
            self.save(filepath=filepath, items=items)
            self.log.info("%s - Remove: %s from %s", self.config_for, key, filepath)
            removed = True
        return removed


class MiAZConfigApp(MiAZConfig):
    def __init__(self, app):
        self.app = app
        self.util = self.app.get_service('util')
        ENV = self.app.get_env()
        GObject.GObject.__init__(self)
        GObject.signal_new('repo-settings-updated-app',
                            MiAZConfigApp,
                            GObject.SignalFlags.RUN_LAST, None, () )
        super().__init__(
            app = app,
            log=MiAZLog('MiAZ.Config.App'),
            config_for = 'App',
            available = ENV['FILE']['CONF'],
            used = ENV['FILE']['CONF'],
            default = None,
            must_copy = False
        )

    def exists(self, key: str) -> bool:
        config = self.load(self.used)
        return key in config

    def save(self, filepath: str = '', items: dict = {}) -> bool:
        saved = self.save_data(filepath, items)
        if saved:
            self.emit('repo-settings-updated-app')
        return saved

class MiAZConfigRepositories(MiAZConfig):
    def __init__(self, app):
        ENV = app.get_env()
        dir_conf = ENV['LPATH']['ETC']
        super().__init__(
            app = app,
            log=MiAZLog('MiAZ.Settings.Repos'),
            config_for = 'Repositories',
            available = os.path.join(dir_conf, 'repos-available.json'),
            used = os.path.join(dir_conf, 'repos-used.json'),
            default = None,
            model = Repository,
            must_copy = False,
            foreign = True
        )

class MiAZConfigCountries(MiAZConfig):
    def __init__(self, app, dir_conf):

        ENV = app.get_env()
        super().__init__(
            app = app,
            log=MiAZLog('MiAZ.Settings.Countries'),
            config_for = 'Countries',
            available = os.path.join(dir_conf, 'countries-available.json'),
            used = os.path.join(dir_conf, 'countries-used.json'),
            default = os.path.join(ENV['GPATH']['CONF'],
                            'MiAZ-countries.json'),
            model = Country,
            must_copy = False,
            foreign = True
        )

class MiAZConfigGroups(MiAZConfig):
    def __init__(self, app, dir_conf):

        ENV = app.get_env()
        super().__init__(
            app = app,
            log=MiAZLog('MiAZ.Settings.Groups'),
            config_for = 'Groups',
            used = os.path.join(dir_conf, 'groups-used.json'),
            available = os.path.join(dir_conf, 'groups-available.json'),
            default = os.path.join(ENV['GPATH']['CONF'],
                            'MiAZ-groups.json'),
            model = Group,
            must_copy = True
        )

class MiAZConfigPurposes(MiAZConfig):
    def __init__(self, app, dir_conf):

        ENV = app.get_env()
        super().__init__(
            app = app,
            log=MiAZLog('MiAZ.Settings.Purposes'),
            config_for = 'Purposes',
            used = os.path.join(dir_conf, 'purposes-used.json'),
            available = os.path.join(dir_conf, 'purposes-available.json'),
            default = os.path.join(ENV['GPATH']['CONF'],
                            'MiAZ-purposes.json'),
            model = Purpose,
            must_copy = True
        )

class MiAZConfigConcepts(MiAZConfig):
    def __init__(self, app, dir_conf):
        super().__init__(
            app = app,
            log=MiAZLog('MiAZ.Settings.Concepts'),
            config_for = 'Concepts',
            used = os.path.join(dir_conf, 'concepts-used.json'),
            available = os.path.join(dir_conf, 'concepts-available.json'),
            default = None,
            model = Concept,
            must_copy = False
        )

class MiAZConfigPeople(MiAZConfig):
    def __init__(self, app, dir_conf):

        ENV = app.get_env()
        super().__init__(
            app = app,
            log=MiAZLog('MiAZ.Settings.People'),
            config_for = 'Person',
            used = os.path.join(dir_conf, 'people-used.json'),
            available = os.path.join(dir_conf, 'people-available.json'),
            default = os.path.join(ENV['GPATH']['CONF'],
                            'MiAZ-people.json'),
            model = Person,
            must_copy = True
        )

class MiAZConfigSentBy(MiAZConfig):
    def __init__(self, app, dir_conf):

        ENV = app.get_env()
        config_name_available = SentBy.__config_name_available__
        config_name_used = SentBy.__config_name_used__
        super().__init__(
            app = app,
            log=MiAZLog('MiAZ.Settings.SentBy'),
            config_for = 'SentBy',
            used = os.path.join(dir_conf, '%s-used.json' % config_name_used),
            available = os.path.join(dir_conf, '%s-available.json' % config_name_available),
            default = os.path.join(ENV['GPATH']['CONF'],
                            'MiAZ-people.json'),
            model = SentBy,
            must_copy = False
        )

class MiAZConfigSentTo(MiAZConfig):
    def __init__(self, app, dir_conf):

        ENV = app.get_env()
        super().__init__(
            app = app,
            log=MiAZLog('MiAZ.Settings.SentTo'),
            config_for = 'SentTo',
            used = os.path.join(dir_conf, '%s-used.json' % SentTo.__config_name_used__),
            available = os.path.join(dir_conf, '%s-available.json' % SentTo.__config_name_available__),
            default = os.path.join(ENV['GPATH']['CONF'],
                            'MiAZ-people.json'),
            model = SentTo,
            must_copy = False
        )

class MiAZConfigProjects(MiAZConfig):
    def __init__(self, app, dir_conf):
        super().__init__(
            app = app,
            log=MiAZLog('MiAZ.Settings.Project'),
            config_for = 'Project',
            used = os.path.join(dir_conf, 'project-used.json'),
            available = os.path.join(dir_conf, 'project-available.json'),
            default = None,
            model = Project,
            must_copy = False
        )

class MiAZConfigUserPlugins(MiAZConfig):
    def __init__(self, app, dir_conf):
        super().__init__(
            app = app,
            log=MiAZLog('MiAZ.Settings.UserPlugins'),
            config_for = 'UserPlugin',
            used = os.path.join(dir_conf, 'plugins-used.json'),
            available = os.path.join(dir_conf, 'plugins-available.json'),
            default = None,
            model = Plugin,
            must_copy = False
        )
