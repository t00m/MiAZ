#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import glob

from MiAZ.backend.env import ENV
from MiAZ.backend.util import load_json
from MiAZ.backend.util import guess_datetime



f_countries = os.path.join(ENV['GPATH']['RESOURCES'], 'miaz-countries.json')
countries = load_json(f_countries)

f_extensions = os.path.join(ENV['GPATH']['RESOURCES'], 'miaz-extensions.json')
extensions = load_json(f_extensions)


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
    reasons = "OK"
    valid = True
    reasons = []

    # Check filename
    dot = filename.rfind('.')
    if dot > 0:
        name = filename[:dot]
        ext = filename[dot+1:]
    else:
        name = filename
        ext = ''
        valid &= False
        reasons.append("Filename not valid. Extension missing.")

    # Check extension
    if ext not in extensions:
        valid &= False
        reasons.append("Extension not allowed")

    # Check fields partitioning
    fields = name.split('-')
    if len(fields) != 5:
        valid &= False
        reasons.append("Wrong number of fields in filename")

    # Check country
    try:
        code = fields[0]
        if not is_country(code):
            valid &= False
            reasons.append("Country code doesn't exist")
    except IndexError:
        valid &= False
        reasons.append("Country code couldn't be checked")

    # Check timestamp
    try:
        timestamp = fields[1]
        if guess_datetime(timestamp) is None:
            valid &= False
            reasons.append("Timestamp not valid")
    except IndexError:
        valid &= False
        reasons.append("Timestamp couldn't be checked")

    return valid, reasons

def workflow():
    docs = get_documents(self.params.SOURCE)
    for doc in docs:
        valid, reasons = valid_filename(doc)
        if not valid:
            print ("%s needs revision. Reasons" % doc)
            for reason in reasons:
                print ("\t => %s" % reason)

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
