import os
import shutil

from MiAZ.backend.env import ENV
from MiAZ.backend.util import json_load, json_save


class MiAZConfig():
    """ MiAZ Config class"""
    config_local = None
    config_global = None

    def __init__(self, log, config_for, config_local=None, config_global=None, config_is=dict, must_copy=True):
        super().__init__()
        self.log = log
        self.config_for = config_for
        self.config_local = config_local
        self.config_global = config_global
        self.config_is = config_is
        self.must_copy = must_copy
        self.setup()

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
            self.log.error(error)
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
            return None

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

    def list_add(self, item):
        config = self.load()
        if not item in config:
            config.append(item.upper())
            self.save(config)
            self.log.info("%s - Add: %s", self.config_for, item)

    def dict_add(self, key, value):
        config = self.load()
        if not key in config:
            config[key] = value.upper()
            self.save(config)
            self.log.info("%s - Add: %s[%s]", self.config_for, key, value)
