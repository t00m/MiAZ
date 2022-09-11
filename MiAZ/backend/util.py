#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
from datetime import datetime

import gi
from gi.repository import Gio

from MiAZ.backend.env import ENV

def get_version() -> str:
    return open(ENV['FILE']['VERSION']).read().strip()

def load_json(filepath: str) -> {}:
    """Load into a dictionary a file in json format"""
    with open(filepath, 'r') as fin:
        adict = json.load(fin)
    return adict

def save_json(filepath: str, adict: {}) -> {}:
    """Save dictionary into a file in json format"""
    with open(filepath, 'w') as fout:
        json.dump(adict, fout)

def get_file_mimetype(path):
    mimetype, val = Gio.content_type_guess('filename=%s' % path, data=None)
    return mimetype

def guess_datetime(sdate):
    """Return (guess) a datetime object for a given string."""
    found = False
    patterns = ["%Y", "%Y%m", "%Y%m%d", "%Y%m%d_%H%M", "%Y%m%d_%H%M%S"]
    for pattern in patterns:
        if not found:
            try:
                td = datetime.strptime(sdate, pattern)
                ts = td.strftime("%Y-%m-%d %H:%M:%S")
                timestamp = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                found = True
            except ValueError:
                timestamp = None
    return timestamp
