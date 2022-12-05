#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import glob
from datetime import datetime
from dateutil import parser as dateparser

from MiAZ.backend.env import ENV
from MiAZ.backend.util import json_load
from MiAZ.backend.util import guess_datetime



def suggest_filename(filepath: str) -> str:
    # "{timestamp}-{country}-{collection}-{from}-{purpose}-{concept}-{to}.{extension}"
    timestamp = ""
    country = ""
    lang = ""
    collection = ""
    organization = ""
    purpose = ""

    filename = os.path.basename(filepath)
    dot = filename.rfind('.')
    if dot > 0:
        name = filename[:dot]
        ext = filename[dot+1:].lower()
    else:
        name = filename
        ext = 'NOEXTENSION'

    fields = name.split('-')

    # ~ Find and/or guess date field
    found_date = False
    for field in fields:
        try:
            adate = dateparser.parse(field[:8])
            if len(timestamp) == 0:
                timestamp = adate.strftime("%Y%m%d")
                found_date = True
        except Exception as error:
            pass
    if not found_date:
        try:
            created = os.stat(filepath).st_ctime
            adate = datetime.fromtimestamp(created)
            timestamp = adate.strftime("%Y%m%d")
        except Exception as error:
            print("%s -> %s" % (filepath, error))
            timestamp = "NODATE"

    # ~ Find and/or guess country field
    found_country = False
    for field in fields:
        if len(field) == 2:
            if is_country(field.upper()):
                country = field.upper()
                found_country = True
    if not found_country:
        country = "DE"

    return "%s-%s-%s-%s-%s.%s" % (timestamp, country, collection, organization, purpose, ext)


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
