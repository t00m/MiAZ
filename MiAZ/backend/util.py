#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import glob
import json
from datetime import datetime
from dateutil.parser import parse as dateparser

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
        json.dump(adict, fout, sort_keys=True, indent=4)

def guess_datetime(adate: str) -> datetime:
    """Return (guess) a datetime object for a given string."""
    try:
        timestamp = dateparser(adate)
    except Exception as error:
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

def get_file_creation_date(filepath: str) -> datetime:
    created = os.stat(filepath).st_ctime
    adate = datetime.fromtimestamp(created)
    return adate #.strftime("%Y%m%d")

def dir_writable(dirpath: str) -> bool:
    try:
        filename = os.path.join(dirpath, 'test.txt')
        with open(filename, 'w') as fout:
            fout.write('test')
            writable = True
        os.unlink(filename)
    except IOError as error:
        writable = False
    except TypeError:
        writable = False
    return writable

def fuzzy_date_from_timestamp(timestamp):
    """
    Convert datetime object to fuzzy time string
    """
    d1 = guess_datetime(timestamp)
    d2 = datetime.now()
    rdate = d2 - d1 # DateTimeDelta
    if rdate.days > 0:
        if rdate.days <= 31:
            return "%d days ago" % int(rdate.days)

        if rdate.days > 31 and rdate.days < 365:
            return "%d months ago" % int((rdate.days/31))

        if rdate.days >= 365:
            return "%d years ago" % int((rdate.days/365))

    hours = rdate.seconds / 3600
    if int(hours) > 0:
        return "%d hours ago" % int(hours)

    minutes = rdate.seconds / 60
    if int(minutes) > 0:
        return "%d minutes ago" % int(minutes)

    if int(rdate.seconds) > 0:
        return "%d seconds ago" % int(rdate.seconds)

    if int(rdate.seconds) == 0:
        return "Right now"
