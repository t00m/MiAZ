#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import glob
from datetime import datetime
from dateutil import parser as dateparser

from MiAZ.backend.env import ENV
from MiAZ.backend.util import load_json
from MiAZ.backend.util import guess_datetime
from MiAZ.backend.config.settings import MiAZConfigSettingsCountries
# ~ from MiAZ.backend.config.settings import MiAZConfigSettingsLanguages
from MiAZ.backend.config.settings import MiAZConfigSettingsExtensions
from MiAZ.backend.config.settings import MiAZConfigSettingsCollections
from MiAZ.backend.config.settings import MiAZConfigSettingsPurposes
from MiAZ.backend.config.settings import MiAZConfigSettingsWho

countries = MiAZConfigSettingsCountries().load_global()
# ~ languages = MiAZConfigSettingsLanguages().load()
extensions = MiAZConfigSettingsExtensions().load()
collections = MiAZConfigSettingsCollections().load()
purposes = MiAZConfigSettingsPurposes().load()
who = organizations = MiAZConfigSettingsWho().load()


def is_country(code: str) -> bool:
    iscountry = False
    try:
        countries[code]
        iscountry = True
    except KeyError:
        iscountry = False
    return iscountry


# ~ def is_lang(code: str) -> bool:
    # ~ islang = False
    # ~ try:
        # ~ languages[code]
        # ~ islang = True
    # ~ except KeyError:
        # ~ islang = False
    # ~ return islang


def suggest_filename(filepath: str) -> str:
    # "{timestamp}-{country}-{collection}-{organization}-{purpose}-{concept}-{who}.{extension}"
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
        # Check extension
        if ext.lower() not in extensions:
            valid &= False
            reasons.append((False, "Extension '%s' not allowed. Add it up first." % ext))
        else:
            reasons.append((True, "Extension '%s' is valid" % ext))
    else:
        name = filename
        ext = ''
        valid &= False
        reasons.append((False, "Filename not valid. Extension missing."))

    # Check fields partitioning
    fields = name.split('-')
    if len(fields) != 7:
        valid &= False
        reasons.append((False, "Wrong number of fields in filename (%d/7)" % len(fields)))
    else:
        reasons.append((True, "Right number of fields in filename (%d/7)" % len(fields)))

    # Check timestamp (1st field)
    try:
        timestamp = fields[0]
        if guess_datetime(timestamp) is None:
            valid &= False
            reasons.append((False, "Field 1. Timestamp '%s' not valid" % timestamp))
        else:
            reasons.append((True, "Field 1. Timestamp '%s' is valid" % timestamp))
    except IndexError:
        valid &= False
        reasons.append((False, "Field 1. Timestamp '%s' couldn't be checked" % timestamp))

    # Check country (2nd field)
    try:
        code = fields[1]
        if not is_country(code):
            valid &= False
            reasons.append((False, "Field 2. Country code '%s' doesn't exist" % code))
        else:
            reasons.append((True, "Field 2. Country code '%s' corresponds to %s" % (code, countries[code]['Country Name'])))
    except IndexError:
        valid &= False
        reasons.append((False, "Field 2. Country code couldn't be checked because this field doesn't exist"))

    # Check collection (3nd field)
    try:
        collection = fields[2]
        if collection not in collections:
            valid &= False
            reasons.append((False, "Field 3. Collection '%s' is not in your list. Please, add it up first." % collection))
        else:
            reasons.append((True, "Field 3. Collection '%s' accepted. It is in your list." % collection))
    except IndexError:
        valid &= False
        reasons.append((False, "Field 3. Collection couldn't be checked because this field doesn't exist"))

    # Check purpose (4th field)
    try:
        purpose = fields[3]
        if purpose not in purposes:
            valid &= False
            reasons.append((False, "Field 4. Purpose '%s' is not in your list. Please, add it up first." % purpose))
        else:
            reasons.append((True, "Field 4. Purpose '%s' accepted. It is in your list." % purpose))
    except IndexError:
        valid &= False
        reasons.append((False, "Field 4. Purpose couldn't be checked because this field doesn't exist"))

    # Check Organization (5th field)
    try:
        organization = fields[4]
        if organization not in organizations:
            valid &= False
            reasons.append((False, "Field 5. Organization '%s' is not in your list. Please, add it up first." % organization))
        else:
            reasons.append((True, "Field 5. Organization '%s' accepted. It is in your list." % organization))
    except IndexError:
        valid &= False
        reasons.append((False, "Field 5. Organization couldn't be checked because this field doesn't exist"))

    # Check Concept (5th field)
    try:
        concept = fields[5]
        reasons.append((True, "Field 6. Concept '%s' accepted" % concept))
        # ~ if organization not in organizations:
            # ~ valid &= False
            # ~ reasons.append((False, "Field 5. Organization '%s' is not in your list. Please, add it up first." % organization))
        # ~ else:
            # ~ reasons.append((True, "Field 5. Organization '%s' accepted. It is in your list." % organization))
    except IndexError:
        valid &= False
        reasons.append((False, "Field 6. Concept couldn't be checked because this field doesn't exist"))


    # Check Who (6th field)
    try:
        org = fields[6]
        if org not in organizations:
            valid &= False
            reasons.append((False, "Field 7. '%s' is not in your list. Please, add it up first." % org))
        else:
            reasons.append((True, "Field 7. Person/Third party '%s' accepted. It is in your list." % org))
    except IndexError:
        valid &= False
        reasons.append((False, "Field 7. Purpose couldn't be checked because this field doesn't exist"))

    # Check language (3rd field)
    # ~ try:
        # ~ code = fields[2]
        # ~ if not is_lang(code):
            # ~ valid &= False
            # ~ reasons.append("Language code '%s' doesn't correspond" % code)
    # ~ except IndexError:
        # ~ valid &= False
        # ~ reasons.append("Language couldn't be checked because this field doesn't exist")

    return valid, reasons


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
