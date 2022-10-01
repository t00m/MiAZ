#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.backend.util import json_load, json_save
from MiAZ.backend.util import valid_key
from MiAZ.backend.util import guess_datetime
from MiAZ.backend.util import get_files
from MiAZ.backend.config.settings import MiAZConfigApp
from MiAZ.backend.config.settings import MiAZConfigSettingsCountries
from MiAZ.backend.config.settings import MiAZConfigSettingsExtensions
from MiAZ.backend.config.settings import MiAZConfigSettingsCollections
from MiAZ.backend.config.settings import MiAZConfigSettingsPurposes
from MiAZ.backend.config.settings import MiAZConfigSettingsWho

# ~ countries = MiAZConfigSettingsCountries().load_global()
# ~ extensions = MiAZConfigSettingsExtensions().load_global()
# ~ collections = MiAZConfigSettingsCollections().load()
# ~ purposes = MiAZConfigSettingsPurposes().load()
# ~ who = organizations = MiAZConfigSettingsWho().load()

class MiAZBackend:
    """Backend class"""
    conf = {}

    def __init__(self) -> None:
        self.log = get_logger('MiAZBackend')
        self.conf['app'] = MiAZConfigApp()
        self.conf['countries'] = MiAZConfigSettingsCountries()
        self.conf['extensions'] = MiAZConfigSettingsExtensions()
        self.conf['collections'] = MiAZConfigSettingsCollections()
        self.conf['purposes'] = MiAZConfigSettingsPurposes()
        self.conf['organizations'] = MiAZConfigSettingsWho()
        self.check_sources()

    def get_conf(self) -> dict:
        """Return dict with pointers to all config classes"""
        return self.conf

    def check_sources(self):
        repodir = self.conf['app'].get('source')
        repokey = valid_key(repodir)
        repocnf = os.path.join(ENV['LPATH']['REPOS'], "source-%s.json" % repokey)
        if os.path.exists(repocnf):
            repodct = json_load(repocnf)
        else:
            repodct = {}
            json_save(repocnf, repodct)

        # Workflow
        ## 1. Check first docs in repodct and delete inconsistencies if
        ## files do not exist anymore
        to_delete = []
        for doc in repodct:
            if not os.path.exists(doc):
                to_delete.append(doc)
                self.log.info("Source repository - Document deleted: %s", doc)
        for doc in to_delete:
            # Delete inconsistency
            del(repodct[doc])
        json_save(repocnf, repodct)

        # 2. Check docs in directory and update repodct
        docs = get_files(repodir)
        for doc in docs:
            try:
                repodct[doc]['valid']
                # ~ self.log.debug("Found in config file: %s", doc)
            except:
                repodct[doc] = {}
                repodct[doc]['valid'] = self.valid_filename(doc)
                self.log.info("Source repository - Document added: %s", doc)
        json_save(repocnf, repodct)

    def valid_filename(self, filepath: str) -> tuple:
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
            ext_allowed = self.conf['extensions'].exists(ext)
            if not ext_allowed:
                valid &= False
                reasons.append((False, "Extension '%s' not allowed. Add it first." % ext))
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

        # "{timestamp}-{country}-{collection}-{from}-{purpose}-{concept}-{to}.{extension}"
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
            is_country = self.conf['countries'].exists(code)
            if not is_country:
                valid &= False
                reasons.append((False, "Field 2. Country code '%s' doesn't exist" % code))
            else:
                country = self.conf['countries'].load_global()
                name = country[code]['Country Name']
                reasons.append((True, "Field 2. Country code '%s' corresponds to %s" % (code, name)))
        except IndexError:
            valid &= False
            reasons.append((False, "Field 2. Country code couldn't be checked because this field doesn't exist"))

        # Check collection (3nd field)
        try:
            code = fields[2]
            is_collection = self.conf['collections'].exists(code)
            if not is_collection:
                valid &= False
                reasons.append((False, "Field 3. Collection '%s' is not in your list. Please, add it first." % code))
            else:
                reasons.append((True, "Field 3. Collection '%s' accepted. It is in your list." % code))
        except IndexError:
            valid &= False
            reasons.append((False, "Field 3. Collection couldn't be checked because this field doesn't exist"))

        # Check from (4th field)
        try:
            code = fields[3]
            is_organization = self.conf['organizations'].exists(code)
            if not is_organization:
                valid &= False
                reasons.append((False, "Field 4. Organization '%s' is not in your list. Please, add it first." % code))
            else:
                reasons.append((True, "Field 4. Organization '%s' accepted. It is in your list." % code))
        except IndexError:
            valid &= False
            reasons.append((False, "Field 4. Organization couldn't be checked because this field doesn't exist"))

        # Check purpose (5th field)
        try:
            code = fields[4]
            is_purpose = self.conf['purposes'].exists(code)
            if not is_purpose:
                valid &= False
                reasons.append((False, "Field 5. Purpose '%s' is not in your list. Please, add it first." % code))
            else:
                reasons.append((True, "Field 5. Purpose '%s' accepted. It is in your list." % code))
        except IndexError:
            valid &= False
            reasons.append((False, "Field 5. Purpose couldn't be checked because this field doesn't exist"))

        # Check Concept (6th field)
        try:
            code = fields[5]
            reasons.append((True, "Field 6. Concept '%s' accepted" % code))
        except IndexError:
            valid &= False
            reasons.append((False, "Field 6. Concept couldn't be checked because this field doesn't exist"))

        # Check Who (7th field)
        try:
            code = fields[6]
            is_organization = self.conf['organizations'].exists(code)
            if not is_organization:
                valid &= False
                reasons.append((False, "Field 7. '%s' is not in your list. Please, add it first." % code))
            else:
                reasons.append((True, "Field 7. Person/Third party '%s' accepted. It is in your list." % code))
        except IndexError:
            valid &= False
            reasons.append((False, "Field 7. Purpose couldn't be checked because this field doesn't exist"))

        return valid, reasons



