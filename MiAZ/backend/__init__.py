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
from MiAZ.backend.config import MiAZConfigApp
from MiAZ.backend.config import MiAZConfigSettingsCountries
from MiAZ.backend.config import MiAZConfigSettingsCollections
from MiAZ.backend.config import MiAZConfigSettingsPurposes
from MiAZ.backend.config import MiAZConfigSettingsConcepts
from MiAZ.backend.config import MiAZConfigSettingsPerson


class MiAZBackend(GObject.GObject):
    """Backend class"""
    __gtype_name__ = 'MiAZBackend'
    conf = {}

    def __init__(self) -> None:
        GObject.GObject.__init__(self)
        self.log = get_logger('MiAZBackend')
        GObject.signal_new('source-configuration-updated',
                            MiAZBackend,
                            GObject.SignalFlags.RUN_LAST, None, () )
        self.conf['App'] = MiAZConfigApp()
        self.conf['Country'] = MiAZConfigSettingsCountries()
        self.conf['Collection'] = MiAZConfigSettingsCollections()
        self.conf['Purpose'] = MiAZConfigSettingsPurposes()
        self.conf['Concept'] = MiAZConfigSettingsConcepts()
        self.conf['SentBy'] = MiAZConfigSettingsPerson()
        self.conf['SentTo'] = MiAZConfigSettingsPerson()
        self.conf['Person'] = MiAZConfigSettingsPerson()
        self.source = self.conf['App'].get('source')
        self.watch_source = MiAZWatcher('source', self.source)
        self.watch_source.connect('source-directory-updated',
                                                    self.check_source)

    def get_watcher_source(self):
        """Get watcher object for source directory"""
        return self.watch_source

    def get_conf(self) -> dict:
        """Return dict with pointers to all config classes"""
        return self.conf

    def get_repo_source_config_file(self):
        """Get config file for current source repository"""
        repodir = self.conf['App'].get('source')
        repokey = valid_key(repodir)
        return os.path.join(ENV['LPATH']['REPOS'], "source-%s.json" %
                                                                repokey)
    def get_repo_dict(self):
        """Load/Create dictionary for current repository"""
        s_repodir = self.conf['App'].get('source')
        s_repocnf = self.get_repo_source_config_file()

        if os.path.exists(s_repocnf):
            s_repodct = json_load(s_repocnf)
        else:
            s_repodct = {}
            json_save(s_repocnf, s_repodct)
        return s_repodct

    def check_source(self, *args):
        s_repodir = self.conf['App'].get('source')
        s_repocnf = self.get_repo_source_config_file()
        s_repodct = self.get_repo_dict()

        # Workflow
        # 1. Check and delete inconsistencies.
        for doc in s_repodct.copy():
            if not os.path.exists(doc):
                del(s_repodct[doc])
                self.log.debug("File[%s] - Inconistency found. Deleted"
                                                        % basename(doc))

        # 2. Rebuild repository dictionary
        docs = get_files(s_repodir)
        for doc in docs:
            valid, reasons = self.validate_filename(doc)
            s_repodct[doc] = {}
            s_repodct[doc]['valid'] = valid
            s_repodct[doc]['reasons'] = reasons
            if not valid:
                s_repodct[doc]['suggested'] = self.suggest_filename(doc)
                s_repodct[doc]['fields'] = ['', '', '', '', '', '', '']
                self.log.debug(reasons)
            else:
                s_repodct[doc]['suggested'] = None
                s_repodct[doc]['fields'] = self.get_fields(doc)
        self.log.info("Repository - %d document analyzed", len(docs))
        json_save(s_repocnf, s_repodct)

        # 3. Emit the 'source-configuration-updated' signal
        self.log.debug("Source repository updated")
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
            valid &= True
            reasons.append((True, "File extension '%s' is valid" % ext))
        else:
            name = filename
            ext = ''
            valid &= False
            reasons.append((False, "File extension missing."))

        # Check fields partitioning
        fields = name.split('-')
        if len(fields) != 7:
            valid &= False
            reasons.append((False, "Wrong number of fields (%d/7)" %
                                                        len(fields)))
        else:
            reasons.append((True, "Right number of fields (%d/7)" %
                                                        len(fields)))

        # Validate fields
        # Check timestamp (1st field)
        try:
            timestamp = fields[0]
            if guess_datetime(timestamp) is None:
                valid &= False
                reasons.append((False, "Timestamp '%s' not valid" %
                                                            timestamp))
            else:
                reasons.append((True, "Timestamp '%s' is valid" %
                                                            timestamp))
        except IndexError:
            valid &= False
            reasons.append((False, "Timestamp couldn't be checked"))

        # Check country (2nd field)
        try:
            code = fields[1].upper()
            is_country = self.conf['Country'].exists(code)
            if not is_country:
                valid &= False
                reasons.append((False,
                                "Country code '%s' doesn't exist" %
                                                                code))
            else:
                country = self.conf['Country'].load_global()
                name = country[code]
                reasons.append((True,
                                "Country code '%s' corresponds to %s" %
                                                        (code, name)))
        except IndexError:
            valid &= False
            reasons.append((False,
                            "Country code couldn't be checked"))

        # Check collection (3nd field)
        try:
            code = fields[2]
            is_collection = self.conf['Collection'].exists(code)
            if not is_collection:
                valid &= False
                reasons.append((False,
                                "Collection '%s' is not in your list. \
                                Please, add it first." % code))
            else:
                reasons.append((True,
                                "Collection '%s' accepted" % code))
        except IndexError:
            valid &= False
            reasons.append((False, "Collection couldn't be checked"))

        # Check SentBy (4th field)
        try:
            code = fields[3]
            is_organization = self.conf['Person'].exists(code)
            if not is_organization:
                valid &= False
                reasons.append((False,
                                "Person '%s' is not in your list. \
                                Please, add it first." % code))
            else:
                reasons.append((True, "Person '%s' accepted" % code))
        except IndexError:
            valid &= False
            reasons.append((False, "Person couldn't be checked"))

        # Check purpose (5th field)
        try:
            code = fields[4]
            is_purpose = self.conf['Purpose'].exists(code)
            if not is_purpose:
                valid &= False
                reasons.append((False,
                                "Purpose '%s' is not in your list. \
                                Please, add it first." % code))
            else:
                reasons.append((True, "Purpose '%s' accepted" % code))
        except IndexError:
            valid &= False
            reasons.append((False, "Purpose couldn't be checked"))

        # Check Concept (6th field)
        try:
            code = fields[5]
            reasons.append((True, "Concept '%s' accepted" % code))
        except IndexError:
            valid &= False
            reasons.append((False, "Concept couldn't be checked"))

        # Check SentTo (7th field)
        try:
            code = fields[6]
            is_organization = self.conf['Person'].exists(code)
            if not is_organization:
                valid &= False
                reasons.append((False,
                                "Person '%s' is not in your list. \
                                Please, add it first." % code))
            else:
                reasons.append((True, "Person '%s' accepted" % code))
        except IndexError:
            valid &= False
            reasons.append((False, "Person couldn't be checked"))

        return valid, reasons


    def suggest_filename(self, filepath: str) -> str:
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
                    # ~ self.log.debug("Found: %s", timestamp)
                    break
            except Exception as error:
                pass
        if not found_date:
            try:
                created = get_file_creation_date(filepath)
                timestamp = created.strftime("%Y%m%d")
                # ~ self.log.debug("Creation date: %s", timestamp)
            except Exception as error:
                # ~ self.log.error("%s -> %s" % (filepath, error))
                timestamp = ""
        # ~ self.log.debug(timestamp)

        # Field 1. Find and/or guess country field
        found_country = False
        for field in fields:
            if len(field) == 2:
                is_country = self.conf['Country'].exists(field.upper())
                if is_country:
                    country = field.upper()
                    found_country = True
                    break
        if not found_country:
            country = ""

        # Field 2. Find and/or guess collection field
        found_collection = False
        for field in fields:
            if self.conf['Collection'].exists(field):
                collection = field.upper()
                found_collection = True
                break
        if not found_collection:
            collection = ''

        # Field 3. Find and/or guess SentBy field
        found_person = False
        for field in fields:
            if self.conf['Person'].exists(field):
                sentby = field.upper()
                found_person = True
                break
        if not found_person:
            sentby = ''

        # Field 4. Find and/or guess purpose field
        found_purpose = False
        for field in fields:
            if self.conf['Purpose'].exists(field):
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

        # Field 6. Find and/or guess SentTo field
        found_person = False
        for field in fields:
            if self.conf['Person'].exists(field):
                found_person = True
                sentto = field.upper()
                break
        if not found_person:
            sentto = ''

        suggested = "%s-%s-%s-%s-%s-%s-%s" % (  timestamp,
                                                country,
                                                collection,
                                                sentby,
                                                purpose,
                                                concept,
                                                sentto)
        # ~ self.log.debug("%s -> %s", filename, suggested)
        return suggested

