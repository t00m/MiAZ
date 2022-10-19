#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil

from gi.repository import GObject

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.backend.util import json_load, json_save
from MiAZ.backend.util import valid_key
from MiAZ.backend.util import guess_datetime
from MiAZ.backend.util import get_files
from MiAZ.backend.util import get_file_creation_date
from MiAZ.backend.watcher import MiAZWatcher
from MiAZ.backend.config.settings import MiAZConfigApp
from MiAZ.backend.config.settings import MiAZConfigSettingsCountries
from MiAZ.backend.config.settings import MiAZConfigSettingsExtensions
from MiAZ.backend.config.settings import MiAZConfigSettingsCollections
from MiAZ.backend.config.settings import MiAZConfigSettingsPurposes
from MiAZ.backend.config.settings import MiAZConfigSettingsConcepts
from MiAZ.backend.config.settings import MiAZConfigSettingsOrganizations


class MiAZBackend(GObject.GObject):
    """Backend class"""
    __gtype_name__ = 'MiAZBackend'
    conf = {}

    def __init__(self) -> None:
        GObject.GObject.__init__(self)
        self.log = get_logger('MiAZBackend')
        GObject.signal_new('source-configuration-updated', MiAZBackend, GObject.SignalFlags.RUN_LAST, None, () )
        GObject.signal_new('target-configuration-updated', MiAZBackend, GObject.SignalFlags.RUN_LAST, None, () )
        self.conf['app'] = MiAZConfigApp()
        self.conf['countries'] = MiAZConfigSettingsCountries()
        self.conf['extensions'] = MiAZConfigSettingsExtensions()
        self.conf['collections'] = MiAZConfigSettingsCollections()
        self.conf['purposes'] = MiAZConfigSettingsPurposes()
        self.conf['concepts'] = MiAZConfigSettingsConcepts()
        self.conf['organizations'] = MiAZConfigSettingsOrganizations()
        self.source = self.conf['app'].get('source')
        self.target = self.conf['app'].get('target')
        self.watch_source = MiAZWatcher('source', self.source)
        self.watch_source.connect('source-directory-updated', self.check_source)
        # ~ self.watch_target = MiAZWatcher('target', self.target)
        # ~ self.watch_target.connect('target-directory-updated', self.check_target)

    def get_watcher_source(self):
        return self.watch_source

    def get_watcher_target(self):
        return self.watch_target

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

    def check_source(self, *args):
        s_repodir = self.conf['app'].get('source')
        s_repocnf = self.get_repo_source_config_file()
        if os.path.exists(s_repocnf):
            s_repodct = json_load(s_repocnf)
        else:
            s_repodct = {}
            json_save(s_repocnf, s_repodct)

        # Workflow
        # 1. Firstly, check files in repodct and delete inconsistencies.
        #    If files do not exist anymore, then delete inconsistency.
        i = 0
        for doc in s_repodct.copy():
            if not os.path.exists(doc):
                del(s_repodct[doc])
                i += 1
        self.log.info("Source repository - %d inconsistencies deleted", i)

        # 2. Then, check docs in source directory and update repodct
        docs = get_files(s_repodir)
        for doc in docs:
            valid, reasons = self.validate_filename(doc)
            s_repodct[doc] = {}
            s_repodct[doc]['valid'] = valid
            s_repodct[doc]['reasons'] = reasons
            if not valid:
                s_repodct[doc]['suggested'] = self.suggest_filename(doc)
            else:
                s_repodct[doc]['suggested'] = None
                s_repodct[doc]['fields'] = self.get_fields(doc)
            # ~ else:
                # ~ doc_target = self.fix_filename(os.path.basename(doc))
                # ~ shutil.move(doc, os.path.join(self.target, doc_target))
                # ~ self.log.debug("Doc[%s] valid. Moved to target folder", os.path.basename(doc))
        self.log.info("Repository - %d document analyzed", len(docs))
        json_save(s_repocnf, s_repodct)

        # 3. Emit the 'source-configuration-updated' signal
        self.log.debug("Source repository - Emitting signal 'source-configuration-updated'")
        self.emit('source-configuration-updated')

    def get_fields(self, filename: str) -> []:
        filename = os.path.basename(filename)
        dot = filename.rfind('.')
        if dot > 0:
            filename = filename[:dot]
        return filename.split('-')

    def fix_filename(self, filename):
        dot = filename.rfind('.')
        if dot > 0:
            name = filename[:dot].upper()
            ext = filename[dot+1:]
        return "%s.%s" % (name, ext)

    # ~ def check_target(self, *args):
        # ~ t_repodir = self.conf['app'].get('target')
        # ~ t_repocnf = self.get_repo_target_config_file()
        # ~ if os.path.exists(t_repocnf):
            # ~ t_repodct = json_load(t_repocnf)
        # ~ else:
            # ~ t_repodct = {}
            # ~ json_save(t_repocnf, t_repodct)

        # ~ # Workflow
        # ~ ## 1. Firstly, check docuements in repodct and delete inconsistencies if
        # ~ ##    files do not exist anymore, then delete inconsistency
        # ~ i = 0
        # ~ for doc in t_repodct.copy():
            # ~ if not os.path.exists(doc):
                # ~ del(t_repodct[doc])
                # ~ i += 1
        # ~ self.log.info("Target repository - %d inconsistencies deleted", i)

        # ~ # 2. Then, check docs in target directory and update repodct
        # ~ a = 0
        # ~ docs = get_files(t_repodir)
        # ~ for filepath in docs:
            # ~ doc = os.path.basename(filepath)
            # ~ if not doc in t_repodct:
                # ~ # Initialize entry
                # ~ t_repodct[doc] = {}
                # ~ a += 1
        # ~ self.log.info("Target repository - %d document added", a)
        # ~ json_save(t_repocnf, t_repodct)

        # ~ # 3. Emit the 'source-configuration-updated' signal
        # ~ self.log.debug("Target repository - Emitting signal 'target-configuration-updated'")
        # ~ self.emit('target-configuration-updated')

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
            code = fields[1].upper()
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
            reasons.append((False, "Field 7. Person/Third party couldn't be checked because this field doesn't exist"))

        return valid, reasons


    def suggest_filename(self, filepath: str) -> str:
        # "{timestamp}-{country}-{collection}-{from}-{purpose}-{concept}-{to}.{extension}"
        timestamp = ""
        country = ""
        lang = ""
        collection = ""
        organization = ""
        purpose = ""
        concept = ""
        extension = ""

        filename = os.path.basename(filepath)
        dot = filename.rfind('.')
        if dot > 0:
            name = filename[:dot]
            ext = filename[dot+1:].lower()
        else:
            name = filename
            ext = ''

        fields = name.split('-')

        # ~ self.log.debug(filename)
        # Field 0. Find and/or guess date field
        found_date = False
        for field in fields:
            # ~ self.log.debug(field)
            try:
                adate = guess_datetime(field[:8])
                timestamp = adate.strftime("%Y%m%d")
                if timestamp is not None:
                    found_date = True
                    break
            except Exception as error:
                pass
        if not found_date:
            try:
                created = get_file_creation_date(filepath)
                timestamp = created.strftime("%Y%m%d")
            except Exception as error:
                self.log.error("%s -> %s" % (filepath, error))
                timestamp = ""
        # ~ self.log.debug(timestamp)
        # Field 1. Find and/or guess country field
        found_country = False
        for field in fields:
            if len(field) == 2:
                is_country = self.conf['countries'].exists(field.upper())
                if is_country:
                    country = field.upper()
                    found_country = True
                    break
        if not found_country:
            country = ""

        # Field 2. Find and/or guess collection field
        found_collection = False
        for field in fields:
            if self.conf['collections'].exists(field):
                collection = field.upper()
                found_collection = True
                break
        if not found_collection:
            collection = ''

        # Field 3. Find and/or guess From field
        found_from = False
        for field in fields:
            if self.conf['organizations'].exists(field):
                from_org = field.upper()
                found_from = True
                break
        if not found_from:
            from_org = ''

        # Field 4. Find and/or guess purpose field
        found_purpose = False
        for field in fields:
            if self.conf['purposes'].exists(field):
                purpose = field.upper()
                found_purpose = True
                break
        if not found_purpose:
            purpose = ''

        # Field 4. Do NOT find and/or guess concept field. Free field.
        try:
            concept = fields[5]
        except:
            concept = ''

        # Field 6. Find and/or guess To field
        found_to = False
        for field in fields:
            if self.conf['organizations'].exists(field):
                found_to = True
                to_org = field.upper()
                break
        if not found_to:
            to_org = ''

        # "{timestamp}-{country}-{collection}-{from}-{purpose}-{concept}-{to}.{extension}"
        suggested = "%s-%s-%s-%s-%s-%s-%s" % (timestamp, country, collection, from_org, purpose, concept, to_org)
        # ~ self.log.debug("%s -> %s", filename, suggested)
        return suggested

