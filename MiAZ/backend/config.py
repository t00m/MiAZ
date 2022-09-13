#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from MiAZ.backend.env import ENV
from MiAZ.backend.util import load_json, save_json


class MiAZConfig():
    """ MiAZ Config class"""
    def __init__(self):
        super(MiAZConfig, self).__init__()
        self.config = self.load_config()
        if self.config is None:
            self.save_config({})
            self.config = self.load_config()

    def load_config(self) -> dict:
        try:
            return load_json(ENV['FILE']['CONF'])
        except (FileNotFoundError, IOError):
            return None


    def save_config(self, config: dict) -> bool:
        saved = False
        try:
            save_json(ENV['FILE']['CONF'], config)
            saved = True
        except Exception as error:
            print(error)
        return saved

    def get(self, key: str) -> str:
        if self.config is not None:
            return self.config[key]
        return None

    def set(self, key: str, value: str) -> None:
        if self.config is not None:
            self.config[key] = value
            self.save_config(self.config)
