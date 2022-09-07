#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import glob

from util import load_json
from util import guess_datetime


countries = load_json('../data/myaz-countries.json')


def is_country(code: str) -> bool:
    iscountry = False
    try:
        countries[code]
        iscountry = True
    except KeyError:
        iscountry = False
    return iscountry


def valid_filename(filepath: str) -> bool:
    filename = os.path.basename(filepath)

    # Check filename extension
    dot = filename.rfind('.')
    if dot > 0:
        name = filename[:dot]
        # ext = filename[dot+1:]
    else:
        return False

    # Check fields partitioning
    fields = name.split('-')
    if len(fields) != 5:
        return False

    # Check country
    code = fields[0]
    if not is_country(code):
        return False

    # Check timestamp
    timestamp = fields[1]
    if guess_datetime(timestamp) is None:
        return False

    return True


def get_documents(root_dir: str) -> []:
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
