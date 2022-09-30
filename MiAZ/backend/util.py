#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import glob
import json
from datetime import datetime

from MiAZ.backend.env import ENV

def get_version() -> str:
    return open(ENV['FILE']['VERSION']).read().strip()

def json_load(filepath: str) -> {}:
    """Load into a dictionary a file in json format"""
    with open(filepath, 'r') as fin:
        adict = json.load(fin)
    return adict

def json_save(filepath: str, adict: {}) -> {}:
    """Save dictionary into a file in json format"""
    with open(filepath, 'w') as fout:
        json.dump(adict, fout)

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

def valid_key(key):
    key = str(key).strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', key)

def get_files(root_dir: str) -> []:
    """Get documents from a given directory recursively
    Avoid hidden documents and documents from hidden directories.
    """
    documents = set()
    hidden = set()
    subdirs = set()

    subdirs.add(os.path.abspath(root_dir))
    for root, dirs, files in os.walk(os.path.abspath(root_dir)):
        thisdir = os.path.abspath(root)
        if os.path.basename(thisdir).startswith('.'):
            hidden.add(thisdir)
        else:
            found = False
            for hidden_dir in hidden:
                if hidden_dir in thisdir:
                    found = True
            if not found:
                subdirs.add(thisdir)
    for directory in subdirs:
        files = glob.glob(os.path.join(directory, '*'))
        for thisfile in files:
            if not os.path.isdir(thisfile):
                if not os.path.basename(thisfile).startswith('.'):
                    documents.add(thisfile)
    return documents