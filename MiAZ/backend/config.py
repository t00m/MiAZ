#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from MiAZ.backend.env import ENV
from MiAZ.backend.util import load_json, save_json


def load_config() -> dict:
    try:
        return load_json(ENV['FILE']['CONF'])
    except (FileNotFoundError, IOError):
        return None


def save_config(config: dict) -> bool:
    saved = False
    try:
        save_json(ENV['FILE']['CONF'], config)
        saved = True
    except Exception as error:
        print(error)
    return saved
