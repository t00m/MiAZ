import os
import shutil

from MiAZ.backend.env import ENV
from MiAZ.backend.util import load_json, save_json


class MiAZConfig():
    """ MiAZ Config class"""
    config_local = None
    config_global = None

    def __init__(self, log, config_for, config_local=None, config_global=None, must_copy=True):
        super().__init__()
        self.log = log
        self.config_for = config_for
        self.config_local = config_local
        self.config_global = config_global
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
                self.save({})

    def load(self) -> dict:
        try:
            config = load_json(self.config_local)
        except Exception as error:
            config = None
            self.log.error(error)
        return config

    def load_global(self) -> dict:
        try:
            items = load_json(self.config_global)
        except Exception as error:
            items = None
            self.log.error(error)
        return items

    def save(self, items: dict) -> bool:
        try:
            save_json(self.config_local, items)
            self.log.debug("%s - Local config file saved", self.config_for)
            saved = True
        except Exception as error:
            self.log.error(error)
            saved = False
        return saved

    def get(self, key: str) -> str:
        config = self.load()
        return config[key]

    def set(self, key: str, value: str) -> None:
        config = self.load()
        config[key] = value
        self.save(config)