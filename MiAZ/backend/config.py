
"""
# File: config.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: App configuration
"""

import os
import shutil
from gettext import gettext as _

from gi.repository import GObject

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import MiAZModel, Group, Person, Country, Purpose, Concept, SentBy, SentTo, Repository, Plugin


def changed_keys(old: dict, new: dict) -> set:
    """The keys that differ between two versions of a config file.

    A key counts as changed when it was added, removed, or kept with a
    different description. Nothing else about the two dicts matters.
    """
    keys = set(old) ^ set(new)
    keys.update(k for k in set(old) & set(new) if old[k] != new[k])
    return keys


class MiAZConfig(GObject.GObject):
    """ MiAZ Config class"""
    __gsignals__ = {
        # Both carry the set of keys that changed, so a listener can drop one
        # cache entry instead of the whole cache. None means the previous
        # contents could not be read, so the receiver must assume everything.
        'available-updated': (GObject.SignalFlags.RUN_LAST, None, (object,)),
        'used-updated': (GObject.SignalFlags.RUN_LAST, None, (object,)),
    }
    used = None
    default = None

    def __init__(self, app, log, config_for, used=None, available=None, default=None, model=MiAZModel, must_copy=True, foreign=False, cache=None):
        super().__init__()
        self.app = app
        self.log = log
        self.config_for = config_for
        self.used = used
        self.available = available
        self.default = default
        self.model = model
        self.must_copy = must_copy
        self.foreign = foreign
        # In-memory copies keyed by absolute filepath. The owner passes the dict
        # in: MiAZConfigStore hands the same one to every config of a repository,
        # because SentBy, SentTo and People all point their "available" pool at
        # people-available.json and must not hold divergent copies of it. It used
        # to be a class attribute, which fixed that but tied the cache lifetime
        # to the process rather than to the repository, so entries from a
        # repository switched away from stayed and were read again on the way
        # back.
        self.cache = {} if cache is None else cache
        self.setup()

    def __repr__(self):
        return __class__.__name__

    def setup(self):
        if not os.path.exists(self.available):
            if self.default is not None:
                try:
                    shutil.copy(self.default, self.available)
                    self.log.debug(f"{self.config_for} - Available configuration created from default")
                    self.log.debug(f"{self.config_for} - Config file path: {self.available}")
                except FileNotFoundError as error:
                    self.log.error(error)
                    if '.conf/plugins' in self.default:
                        self.log.error("It is very likely the problem is coming from a plugin")
                        self.log.error("The file with factory data hasn't been found")
                        self.log.error("The plugin should generate this file during the start up")

            else:
                self.save(filepath=self.available, items={})
                self.log.debug(f"{self.config_for} - Available configuration file created (empty)")
                self.log.debug(f"{self.config_for} - Config file path: {self.available}")

        if not os.path.exists(self.used):
            self.save(filepath=self.used, items={})
            self.log.debug(f"{self.config_for} - Used configuration file created (empty)")

    def get_config_for(self):
        return self.config_for

    def get_used(self):
        return self.used

    def get_default(self):
        return self.default

    def get_config_foreign(self):
        return self.foreign

    def load(self, filepath: str) -> dict:
        util = self.app.get_service('util')
        try:
            config_changed = self.cache[filepath]['changed']
        except KeyError:
            config_changed = True


        if config_changed:
            # ~ self.log.debug(f"Loading {self.config_for} items from disk ({filepath})!!")
            try:
                items = util.json_load(filepath)
                self.cache[filepath] = {}
                self.cache[filepath]['changed'] = False
                self.cache[filepath]['items'] = items
                # ~ self.log.debug(f"In-memory config data updated for '{filepath}'")
            except Exception as error:
                self.log.error(f"Failed to load config from {filepath}: {error}")
                items = {}
            return items
        else:
            # ~ self.log.debug(f"Loading {self.config_for} items from cache ({filepath})")
            self.cache[filepath]['changed'] = False
            return self.cache[filepath]['items']

    def load_available(self) -> dict:
        # ~ self.log.debug(f"{self.config_for} available: {self.available}")
        return self.load(self.available)

    def load_used(self) -> dict:
        # ~ self.log.debug(f"{self.config_for} used: {self.used}")
        return self.load(self.used)

    def save(self, filepath: str = '', items: dict = None) -> bool:
        if items is None:
            items = {}
        # Resolve the default here rather than only inside save_data. It used to
        # be resolved there alone, so a caller passing no filepath (set() did)
        # wrote the right file but invalidated self.cache[''] and emitted no
        # signal at all.
        if not filepath:
            filepath = self.used
        # Read the previous contents before overwriting them. The diff cannot be
        # taken against self.cache: load() hands out the cached dict itself and
        # callers mutate it in place (set() does), so by now the cached copy is
        # already the new one.
        previous = self._read_from_disk(filepath)
        saved = self.save_data(filepath, items)
        if saved:
            self._invalidate(filepath)
            changed = None if previous is None else changed_keys(previous, items)
            if filepath == self.available:
                self.emit('available-updated', changed)
            elif filepath == self.used:
                self.log.debug(f"Signal emitted after saving used config for {self.config_for}")
                self.emit('used-updated', changed)
        return saved

    def _read_from_disk(self, filepath: str):
        """The file as it is on disk right now, or None when it cannot be read.

        A missing file is not a failure: it means every key in what is about to
        be written is new. None is reserved for a read that went wrong, which
        the signal passes on so listeners fall back to clearing everything.
        """
        if not filepath or not os.path.exists(filepath):
            return {}
        util = self.app.get_service('util')
        try:
            return util.json_load(filepath)
        except Exception as error:
            self.log.warning(f"Could not read {filepath} before saving: {error}")
            return None

    def _invalidate(self, filepath: str):
        """Mark the on-disk copy as newer than the cached one."""
        self.cache.setdefault(filepath, {})['changed'] = True

    def save_available(self, items: dict = None) -> bool:
        if items is None:
            items = {}
        return self.save(self.available, items)

    def save_used(self, items: dict = None) -> bool:
        if items is None:
            items = {}
        return self.save(self.used, items)

    def save_data(self, filepath: str = '', items: dict = None) -> bool:
        if items is None:
            items = {}
        util = self.app.get_service('util')
        if filepath == '':
            filepath = self.used
        try:
            util.json_save(filepath, items)
            saved = True
        except Exception as error:
            self.log.error(error)
            saved = False
        return saved

    def get(self, key: str) -> str:
        config = self.load(self.used)
        try:
            return config[key]
        except KeyError:
            return None

    def set(self, key: str, value: str) -> bool:
        items = self.load(self.used)
        items[key] = value
        return self.save(self.used, items=items)

    def exists_used(self, key: str) -> bool:
        config = self.load(self.used)
        return key in config

    def exists_available(self, key: str) -> bool:
        config = self.load(self.available)
        return key in config

    def _add_batch(self, filepath: str, keysvalues: list):
        util = self.app.get_service('util')
        items = self.load(filepath)
        saved = 0
        for key, value in keysvalues:
            if len(key.strip()) != 0:
                key = util.valid_key(key)
                items[key] = value
                saved += 1
        if saved > 0:
            self.save(filepath, items=items)
            self.log.info(f"{self.config_for} - Added {saved} keys to {filepath}")

    def add_available_batch(self, keysvalues: list):
        self._add_batch(self.available, keysvalues)

    def add_available(self, key: str, value: str = ''):
        self.add(self.available, key, value)

    def add_used_batch(self, keysvalues: list):
        self._add_batch(self.used, keysvalues)

    def add_used(self, key: str, value: str = '') -> bool:
        return self.add(self.used, key, value)

    def add(self, filepath: str, key: str, value: str = '') -> bool:
        util = self.app.get_service('util')
        added = True
        if len(key.strip()) == 0:
            self.log.warning('Key is None or empty. Add skipped')
            return False
        items = self.load(filepath)
        if key not in items:
            key = util.valid_key(key)
            items[key] = value
            self.save(filepath, items=items)
            self.log.info(f"{self.config_for} - Add: '{key}' to {filepath}")
            added = True
        return added

    def remove_all(self):
        self.save_available(items={})

    def remove_available_batch(self, keys: list):
        self.remove_batch(self.available, keys)

    def remove_used_batch(self, keys: list):
        self.remove_batch(self.used, keys)

    def remove_available(self, key: str):
        return self.remove(self.available, key)

    def remove_used(self, key: str) -> bool:
        return self.remove(self.used, key)

    def remove_batch(self, filepath: str, keys: list):
        items = self.load(filepath)
        for key in keys:
            if key in items:
                del items[key]
                self.log.info(f"{self.config_for} - Remove: {key} from {filepath}")
        self.save(filepath=filepath, items=items)

    def remove(self, filepath: str, key: str) -> bool:
        removed = False
        if key is None or key.strip() == '':
            self.log.warning('Key is None or empty. Remove skipped')
            return False
        items = self.load(filepath)
        if key in items:
            del items[key]
            self.save(filepath=filepath, items=items)
            self.log.info(f"{self.config_for} - Remove: {key} from {filepath}")
            removed = True
        return removed


class MiAZConfigApp(MiAZConfig):
    __gsignals__ = {
        'repo-settings-updated-app': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, app):
        self.app = app
        ENV = self.app.get_env()
        super().__init__(
            app=app,
            log=MiAZLog('MiAZ.Config.App'),
            config_for=_('App'),
            available=ENV['FILE']['CONF'],
            used=ENV['FILE']['CONF'],
            default=None,
            must_copy=False
        )

    def exists(self, key: str) -> bool:
        config = self.load(self.used)
        return key in config

    def save(self, filepath: str = '', items: dict = None) -> bool:
        if items is None:
            items = {}
        if not filepath:
            filepath = self.used
        saved = self.save_data(filepath, items)
        if saved:
            # The base class emits available-updated / used-updated; this config
            # points both at the same file and announces itself instead. The
            # cache still has to be invalidated, which this override used to skip.
            self._invalidate(filepath)
            self.emit('repo-settings-updated-app')
        return saved


class MiAZConfigRepositories(MiAZConfig):
    def __init__(self, app):
        ENV = app.get_env()
        dir_conf = ENV['LPATH']['ETC']
        super().__init__(
            app=app,
            log=MiAZLog('MiAZ.Config.Repos'),
            config_for=_('Repositories'),
            available=os.path.join(dir_conf, 'repos-available.json'),
            used=os.path.join(dir_conf, 'repos-used.json'),
            default=None,
            model=Repository,
            must_copy=False,
            foreign=True
        )

    @staticmethod
    def _normalize_items(items: dict):
        """Convert the legacy {key: path} shape into the current
        {key: {'path': path, 'description': desc}} shape.
        """
        changed = False
        normalized = {}
        for key, value in items.items():
            if isinstance(value, dict):
                path = value.get('path', '')
                desc = value.get('description', '')
                normalized[key] = {'path': path, 'description': desc}
                if 'path' not in value or 'description' not in value:
                    changed = True
            else:
                # Legacy format: the value is the repository path string
                normalized[key] = {'path': value or '', 'description': ''}
                changed = True
        return normalized, changed

    def load(self, filepath: str) -> dict:
        items = super().load(filepath)
        normalized, changed = self._normalize_items(items)
        if changed:
            # Migrate in place. Write directly with the util service instead of
            # self.save() so we don't emit available-updated/used-updated in the
            # middle of a read (which would trigger redundant view refreshes).
            util = self.app.get_service('util')
            util.json_save(filepath, normalized)
            self.cache[filepath] = {'changed': False, 'items': normalized}
            self.log.debug(f"Migrated repository config to new format: {filepath}")
        return normalized

    def get_path(self, key: str, used: bool = True) -> str:
        items = self.load(self.used if used else self.available)
        entry = items.get(key)
        if isinstance(entry, dict):
            return entry.get('path', '')
        return entry or ''

    def get_description(self, key: str, used: bool = True) -> str:
        items = self.load(self.used if used else self.available)
        entry = items.get(key)
        if isinstance(entry, dict):
            return entry.get('description', '')
        return ''

    def set_repo(self, key: str, path: str, description: str = '', used: bool = True) -> bool:
        filepath = self.used if used else self.available
        items = self.load(filepath)
        items[key] = {'path': path or '', 'description': description or ''}
        return self.save(filepath, items)

    def set_repo_available(self, key: str, path: str, description: str = '') -> bool:
        return self.set_repo(key, path, description, used=False)

    def set_repo_used(self, key: str, path: str, description: str = '') -> bool:
        return self.set_repo(key, path, description, used=True)


class MiAZConfigCountries(MiAZConfig):
    def __init__(self, app, dir_conf, cache=None):

        ENV = app.get_env()
        super().__init__(
            app=app,
            log=MiAZLog('MiAZ.Config.Countries'),
            config_for=_('Countries'),
            available=os.path.join(dir_conf, 'countries-available.json'),
            used=os.path.join(dir_conf, 'countries-used.json'),
            default=os.path.join(ENV['GPATH']['CONF'], 'MiAZ-countries.json'),
            model=Country,
            must_copy=False,
            foreign=True,
            cache=cache
        )


class MiAZConfigGroups(MiAZConfig):
    def __init__(self, app, dir_conf, cache=None):

        ENV = app.get_env()
        super().__init__(
            app=app,
            log=MiAZLog('MiAZ.Config.Groups'),
            config_for=_('Groups'),
            used=os.path.join(dir_conf, 'groups-used.json'),
            available=os.path.join(dir_conf, 'groups-available.json'),
            default=os.path.join(ENV['GPATH']['CONF'], 'MiAZ-groups.json'),
            model=Group,
            must_copy=True,
            cache=cache
        )


class MiAZConfigPurposes(MiAZConfig):
    def __init__(self, app, dir_conf, cache=None):
        ENV = app.get_env()
        super().__init__(
            app=app,
            log=MiAZLog('MiAZ.Config.Purposes'),
            config_for=_('Purposes'),
            used=os.path.join(dir_conf, 'purposes-used.json'),
            available=os.path.join(dir_conf, 'purposes-available.json'),
            default=os.path.join(ENV['GPATH']['CONF'], 'MiAZ-purposes.json'),
            model=Purpose,
            must_copy=True,
            cache=cache
        )


class MiAZConfigConcepts(MiAZConfig):
    def __init__(self, app, dir_conf, cache=None):
        super().__init__(
            app=app,
            log=MiAZLog('MiAZ.Config.Concepts'),
            config_for=_('Concepts'),
            used=os.path.join(dir_conf, 'concepts-used.json'),
            available=os.path.join(dir_conf, 'concepts-available.json'),
            default=None,
            model=Concept,
            must_copy=False,
            cache=cache
        )


class MiAZConfigPeople(MiAZConfig):
    def __init__(self, app, dir_conf, cache=None):

        ENV = app.get_env()
        super().__init__(
            app=app,
            log=MiAZLog('MiAZ.Config.People'),
            config_for=_('Person'),
            used=os.path.join(dir_conf, 'people-used.json'),
            available=os.path.join(dir_conf, 'people-available.json'),
            default=os.path.join(ENV['GPATH']['CONF'], 'MiAZ-people.json'),
            model=Person,
            must_copy=True,
            cache=cache
        )


class MiAZConfigSentBy(MiAZConfig):
    def __init__(self, app, dir_conf, cache=None):

        ENV = app.get_env()
        config_name_available = SentBy.__config_name_available__
        config_name_used = SentBy.__config_name_used__
        super().__init__(
            app=app,
            log=MiAZLog('MiAZ.Config.SentBy'),
            config_for=_('Senders'),
            used=os.path.join(dir_conf, f'{config_name_used}-used.json'),
            available=os.path.join(dir_conf, f'{config_name_available}-available.json'),
            default=os.path.join(ENV['GPATH']['CONF'], 'MiAZ-people.json'),
            model=SentBy,
            must_copy=False,
            cache=cache
        )


class MiAZConfigSentTo(MiAZConfig):
    def __init__(self, app, dir_conf, cache=None):

        ENV = app.get_env()
        super().__init__(
            app=app,
            log=MiAZLog('MiAZ.Config.SentTo'),
            config_for=_('Recipients'),
            used=os.path.join(dir_conf, f'{SentTo.__config_name_used__}-used.json'),
            available=os.path.join(dir_conf, f'{SentTo.__config_name_available__}-available.json'),
            default=os.path.join(ENV['GPATH']['CONF'], 'MiAZ-people.json'),
            model=SentTo,
            must_copy=False,
            cache=cache
        )


class MiAZConfigPlugins(MiAZConfig):
    def __init__(self, app, dir_conf, cache=None):
        super().__init__(
            app=app,
            log=MiAZLog('MiAZ.Config.Plugins'),
            config_for=_('Plugin'),
            used=os.path.join(dir_conf, 'plugins-used.json'),
            available=os.path.join(dir_conf, 'plugins-available.json'),
            default=None,
            model=Plugin,
            must_copy=False,
            cache=cache
        )


# Every configuration a repository owns, by the name the rest of the app uses
# with app.get_config(name).
REPO_CONFIGS = (
    ('Country', MiAZConfigCountries),
    ('Group', MiAZConfigGroups),
    ('Purpose', MiAZConfigPurposes),
    ('Concept', MiAZConfigConcepts),
    ('SentBy', MiAZConfigSentBy),
    ('SentTo', MiAZConfigSentTo),
    ('Person', MiAZConfigPeople),
    ('Plugin', MiAZConfigPlugins),
)


class MiAZConfigStore:
    """Owns every configuration of one repository, and their shared cache.

    One store per repository, disposed when the repository is switched away
    from. The cache used to be a class attribute on MiAZConfig: shared by every
    instance in the process, which is what the configs of a repository need
    (SentBy, SentTo and Person all read people-available.json), but keyed by
    absolute filepath and never emptied, so entries survived the switch and were
    read again on the way back.
    """

    def __init__(self, app, dir_conf):
        self.app = app
        self.dir_conf = dir_conf
        self.log = MiAZLog('MiAZ.Config.Store')
        self.cache = {}
        self._configs = {}
        for name, klass in REPO_CONFIGS:
            self._configs[name] = klass(app, dir_conf, cache=self.cache)
        self.log.debug(f"Configuration loaded for repository: {dir_conf}")

    def get(self, name: str):
        """One configuration by name, or None."""
        return self._configs.get(name)

    def names(self):
        """The names this store holds."""
        return list(self._configs)

    def as_dict(self) -> dict:
        """The configs keyed by name, for publishing into the app registry."""
        return dict(self._configs)

    def dispose(self):
        """Drop the cache and the configs. Called on a repository switch."""
        self.cache.clear()
        self._configs.clear()
        self.log.debug(f"Configuration disposed for repository: {self.dir_conf}")
