#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from gi.repository import GObject

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.backend.util import json_load, json_save
from MiAZ.backend.util import valid_key
from MiAZ.backend.util import guess_datetime
from MiAZ.backend.util import get_files
from MiAZ.backend.util import get_file_creation_date
from MiAZ.backend.config.settings import MiAZConfigApp
from MiAZ.backend.config.settings import MiAZConfigSettingsCountries
from MiAZ.backend.config.settings import MiAZConfigSettingsExtensions
from MiAZ.backend.config.settings import MiAZConfigSettingsCollections
from MiAZ.backend.config.settings import MiAZConfigSettingsPurposes
from MiAZ.backend.config.settings import MiAZConfigSettingsWho



class MiAZBackend(GObject.GObject):
    """Backend class"""
    __gtype_name__ = 'MiAZBackend'
    conf = {}

    def __init__(self) -> None:
        GObject.GObject.__init__(self)
        self.log = get_logger('MiAZBackend')
        GObject.signal_new('source-updated', MiAZBackend, GObject.SignalFlags.RUN_LAST, None, () )
        self.conf['app'] = MiAZConfigApp()
        self.conf['countries'] = MiAZConfigSettingsCountries()
        self.conf['extensions'] = MiAZConfigSettingsExtensions()
        self.conf['collections'] = MiAZConfigSettingsCollections()
        self.conf['purposes'] = MiAZConfigSettingsPurposes()
        self.conf['organizations'] = MiAZConfigSettingsWho()


    def get_conf(self) -> dict:
        """Return dict with pointers to all config classes"""
        return self.conf

    def get_repo_source_config_file(self):
        repodir = self.conf['app'].get('source')
        repokey = valid_key(repodir)
        return os.path.join(ENV['LPATH']['REPOS'], "source-%s.json" % repokey)

    def get_repo_target_config_file(self):
        repodir = self.conf['app'].get('target')
        repokey = valid_key(repodir)
        return os.path.join(ENV['LPATH']['REPOS'], "target-%s.json" % repokey)

    def check_sources(self):
        updated = False
        s_repodir = self.conf['app'].get('source')
        s_repocnf = self.get_repo_source_config_file()
        if os.path.exists(s_repocnf):
            s_repodct = json_load(s_repocnf)
        else:
            s_repodct = {}
            json_save(s_repocnf, s_repodct)

        # Workflow
        ## 1. Check first docs in repodct and delete inconsistencies if
        ## files do not exist anymore
        to_delete = []
        for doc in s_repodct:
            if not os.path.exists(doc):
                to_delete.append(doc)
                self.log.info("Source repository - Document deleted: %s", doc)
        for doc in to_delete:
            # Delete inconsistency
            del(repodct[doc])
            updated |= True
        json_save(s_repocnf, s_repodct)

        # 2. Check docs in source directory and update repodct
        docs = get_files(s_repodir)
        for doc in docs:
            try:
                repodct[doc]['valid']
                # ~ self.log.debug("Found in config file: %s", doc)
            except:
                s_repodct[doc] = {}
                s_repodct[doc]['original'] = doc
                s_repodct[doc]['valid'] = self.validate_filename(doc)
                s_repodct[doc]['suggested'] = self.suggest_filename(doc)
                updated |= True
                self.log.info("Source repository - Document added: %s", doc)
        json_save(s_repocnf, s_repodct)
        self.log.debug("Repository updated? %s", updated)
        if updated:
            self.emit('source-updated')
            self.log.debug("Signal 'source-updated' emitted")

    def validate_filename(self, filepath: str) -> tuple:
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


    def suggest_filename(self, filepath: str) -> str:
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
                created = get_file_creation_date(filepath)
                timestamp = created.strftime("%Y%m%d")
                # ~ self.log.debug(timestamp)
            except Exception as error:
                print("%s -> %s" % (filepath, error))
                timestamp = "NODATE"

        # ~ Find and/or guess country field
        found_country = False
        for field in fields:
            if len(field) == 2:
                is_country = self.conf['countries'].exists(field.upper())
                if is_country:
                    country = field.upper()
                    found_country = True
        if not found_country:
            country = "DE"

        return "%s-%s-%s-%s-%s.%s" % (timestamp, country, collection, organization, purpose, ext)

