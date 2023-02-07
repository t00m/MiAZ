#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from os.path import basename
import shutil

from gi.repository import GObject

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.backend.util import json_load, json_save
from MiAZ.backend.util import valid_key
from MiAZ.backend.util import guess_datetime
from MiAZ.backend.util import get_files
from MiAZ.backend.util import get_fields
from MiAZ.backend.util import get_file_creation_date
from MiAZ.backend.watcher import MiAZWatcher
from MiAZ.backend.config import MiAZConfigApp
from MiAZ.backend.config import MiAZConfigSettingsCountries
from MiAZ.backend.config import MiAZConfigSettingsGroups
from MiAZ.backend.config import MiAZConfigSettingsSubgroups
from MiAZ.backend.config import MiAZConfigSettingsPurposes
from MiAZ.backend.config import MiAZConfigSettingsConcepts
from MiAZ.backend.config import MiAZConfigSettingsPeople
from MiAZ.backend.config import MiAZConfigSettingsSentBy
from MiAZ.backend.config import MiAZConfigSettingsSentTo
from MiAZ.backend.models import File, Group, Subgroup, Person, Country, Purpose, Concept


class MiAZBackend(GObject.GObject):
    """Backend class"""
    __gtype_name__ = 'MiAZBackend'
    conf = {}
    checking = False

    def __init__(self) -> None:
        GObject.GObject.__init__(self)
        self.log = get_logger('MiAZBackend')
        GObject.signal_new('source-configuration-updated',
                            MiAZBackend,
                            GObject.SignalFlags.RUN_LAST, None, () )
        self.conf['App'] = MiAZConfigApp()

    def repo_validate(self, path: str) -> bool:
        self.log.debug("Checking conf dir: %s", path)
        conf_dir = os.path.join(path, '.conf')
        conf_file = os.path.join(conf_dir, 'repo.json')
        if os.path.exists(conf_dir):
            self.log.debug("Config path '%s' exists", conf_dir)
            if os.path.exists(conf_file):
                repo = json_load(conf_file)
                self.log.debug("Current repository: %s", path)
                self.log.debug("MiAZ Repository format: %s", repo['FORMAT'])
                return True
            else:
                self.log.debug("Repo config file '%s' doesn't exist", conf_file)
                return True
        else:
            self.log.debug("Config dir '%s' doesn't exist", conf_dir)
            return False

    def repo_init(self, path):
        conf = {}
        conf['FORMAT'] = 1
        dir_conf = os.path.join(path, '.conf')
        os.makedirs(dir_conf, exist_ok = True)
        conf_file = os.path.join(dir_conf, 'repo.json')
        json_save(conf_file, conf)
        self.conf['App'].set('source', path)
        self.log.debug("Repo configuration initialized")

    def repo_config(self):
        conf = {}
        conf['dir_docs'] = self.conf['App'].get('source')
        conf['dir_conf'] = os.path.join(conf['dir_docs'], '.conf')
        conf['cnf_file'] = os.path.join(conf['dir_conf'], "source-%s.json" % valid_key(conf['dir_docs']))
        return conf

    def repo_load(self, path):
        conf = self.repo_config()
        dir_conf = conf['dir_conf']
        self.conf['Country'] = MiAZConfigSettingsCountries(dir_conf)
        self.conf['Country'].connect('repo-settings-updated-countries-used', self.repo_check)
        self.conf['Group'] = MiAZConfigSettingsGroups(dir_conf)
        self.conf['Group'].connect('repo-settings-updated-groups-used', self.repo_check)
        self.conf['Subgroup'] = MiAZConfigSettingsSubgroups(dir_conf)
        self.conf['Purpose'] = MiAZConfigSettingsPurposes(dir_conf)
        self.conf['Concept'] = MiAZConfigSettingsConcepts(dir_conf)
        self.conf['SentBy'] = MiAZConfigSettingsSentBy(dir_conf)
        self.conf['SentTo'] = MiAZConfigSettingsSentTo(dir_conf)
        self.conf['Person'] = MiAZConfigSettingsPeople(dir_conf)
        self.watcher = MiAZWatcher('source', path)
        self.watcher.set_active(active=True)
        self.watcher.connect('repository-updated', self.repo_check)
        # ~ self.conf['App'].connect('repo-settings-updated-app', self.foo)
        self.log.debug("Configuration loaded")

    def get_watcher_source(self):
        """Get watcher object for source directory"""
        return self.watch_source

    def get_conf(self) -> dict:
        """Return dict with pointers to all config classes"""
        return self.conf

    def get_repo_dict(self):
        """Load dictionary for current repository"""
        return self.s_repodct

    def repo_check(self, *args):
        if self.checking:
            self.log.debug("Repository check already in progress")
            return
        else:
            self.log.debug("Repository check started")
            self.checking = True

        repo = self.repo_config()
        s_repodir = repo['dir_docs']
        s_repocnf = repo['cnf_file']
        if os.path.exists(s_repocnf):
            self.s_repodct = json_load(s_repocnf)
            self.log.debug("Loading configuration from: %s" % s_repocnf)
        else:
            self.s_repodct = {}
            json_save(s_repocnf, self.s_repodct)
            self.log.debug("Created an empty configuration file in: %s" % s_repocnf)

        # Workflow
        # 1. Check and delete inconsistencies.
        for doc in self.s_repodct.copy():
            if not os.path.exists(doc):
                del(self.s_repodct[doc])
                self.log.debug("File[%s] - Inconistency found. Deleted"
                                                        % basename(doc))

        # 2. Rebuild repository dictionary
        docs = get_files(s_repodir)
        for doc in docs:
            # ~ if doc not in self.s_repodct:
            # ~ self.log.debug("Doc[%s] must be analyzed", doc)
            valid, reasons = self.validate_filename(doc)
            self.s_repodct[doc] = {}
            self.s_repodct[doc]['valid'] = valid
            self.s_repodct[doc]['reasons'] = reasons
            if not valid:
                self.s_repodct[doc]['suggested'] = "-------" # DISABLED: improve peformance # self.suggest_filename(doc)
                self.s_repodct[doc]['fields'] = ['' for fields in range(8)]
                # ~ self.log.debug(reasons)
            else:
                self.s_repodct[doc]['suggested'] = None
                self.s_repodct[doc]['fields'] = get_fields(doc)
        self.log.info("Repository check finished: %d documents analyzed", len(docs))
        json_save(s_repocnf, self.s_repodct)

        # 3. Emit the 'source-configuration-updated' signal
        self.log.debug("Source repository updated")
        self.emit('source-configuration-updated')

    def validate_filename(self, filepath: str) -> tuple:
        filename = os.path.basename(filepath)
        reasons = "OK"
        valid = True
        reasons = []
        partitioning = False

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
        if len(fields) != 8:
            valid &= False
            reasons.append((False, "Wrong number of fields (%d/8)" %
                                                        len(fields)))
        else:
            reasons.append((True, "Right number of fields (%d/8)" %
                                                        len(fields)))
            partitioning = True

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
                default = self.conf['Country'].default
                country = self.conf['Country'].load(default)
                name = country[code]
                reasons.append((True,
                                "Country code '%s' corresponds to %s" %
                                                        (code, name)))
        except IndexError:
            valid &= False
            reasons.append((False,
                            "Country code couldn't be checked"))

        # Check group (3th field)
        try:
            code = fields[2]
            is_group = self.conf['Group'].exists(code)
            if not is_group:
                valid &= False
                reasons.append((False,
                                "Group '%s' is not in your list." \
                                " Please, add it first." % code))
            else:
                reasons.append((True,
                                "Group '%s' accepted" % code))
        except IndexError:
            valid &= False
            reasons.append((False, "Group couldn't be checked"))

        # Check subgroup (4th field)
        try:
            code = fields[3]
            is_subgroup = self.conf['Subgroup'].exists(code)
            if not is_subgroup:
                valid &= False
                reasons.append((False,
                                "Subgroup '%s' is not in your list." \
                                " Please, add it first." % code))
            else:
                reasons.append((True,
                                "Subgroup '%s' accepted" % code))
        except IndexError:
            valid &= False
            reasons.append((False, "Subgroup couldn't be checked"))

        # Check SentBy (5th field)
        try:
            code = fields[4]
            is_people = self.conf['Person'].exists(code)
            if not is_people:
                valid &= False
                reasons.append((False,
                                "Person '%s' is not in your list. " \
                                "Please, add it first." % code))
            else:
                reasons.append((True, "Person '%s' accepted" % code))
        except IndexError:
            valid &= False
            reasons.append((False, "Person couldn't be checked"))

        # Check purpose (6th field)
        try:
            code = fields[5]
            is_purpose = self.conf['Purpose'].exists(code)
            if not is_purpose:
                valid &= False
                reasons.append((False,
                                "Purpose '%s' is not in your list. " \
                                "Please, add it first." % code))
            else:
                reasons.append((True, "Purpose '%s' accepted" % code))
        except IndexError:
            valid &= False
            reasons.append((False, "Purpose couldn't be checked"))

        # Check Concept (7th field)
        try:
            code = fields[6]
            reasons.append((True, "Concept '%s' accepted" % code))
        except IndexError:
            valid &= False
            reasons.append((False, "Concept couldn't be checked"))

        # Check SentTo (8th field)
        try:
            code = fields[7]
            is_people = self.conf['Person'].exists(code)
            if not is_people:
                valid &= False
                reasons.append((False,
                                "Person '%s' is not in your list. " \
                                "Please, add it first." % code))
            else:
                reasons.append((True, "Person '%s' accepted" % code))
        except IndexError:
            valid &= False
            reasons.append((False, "Person couldn't be checked"))

        if partitioning is True:
            self.conf['Group'].add(fields[2].upper())
            self.conf['Subgroup'].add(fields[3].upper())
            self.conf['SentBy'].add(fields[4].upper())
            self.conf['Purpose'].add(fields[5].upper())
            self.conf['SentTo'].add(fields[7].upper())

        return valid, reasons

    def suggest_filename(self, filepath: str, valid: bool = False) -> str:
        timestamp = ""
        country = ""
        group = ""
        subgroup = ""
        person = ""
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

        # Field 2. Find and/or guess group field
        found_group = False
        for field in fields:
            if self.conf['Group'].exists(field):
                group = field.upper()
                found_group = True
                break
        if not found_group:
            group = ''

        # Field 3. Find and/or guess subgroup field
        found_subgroup = False
        for field in fields:
            if self.conf['Subgroup'].exists(field):
                subgroup = field.upper()
                found_subgroup = True
                break
        if not found_subgroup:
            subgroup = ''

        # Field 4. Find and/or guess SentBy field
        found_person = False
        for field in fields:
            if self.conf['Person'].exists(field):
                sentby = field.upper()
                found_person = True
                break
        if not found_person:
            sentby = ''

        # Field 5. Find and/or guess purpose field
        found_purpose = False
        for field in fields:
            if self.conf['Purpose'].exists(field):
                purpose = field.upper()
                found_purpose = True
                break
        if not found_purpose:
            purpose = ''

        # Field 6. Do NOT find and/or guess concept field. Free field.
        if not valid:
            concept = name.replace('-', '_')
        else:
            concept = fields[5]

        # Field 7. Find and/or guess SentTo field
        found_person = False
        for field in fields:
            if self.conf['Person'].exists(field):
                found_person = True
                sentto = field.upper()
                break
        if not found_person:
            sentto = ''

        suggested = "%s-%s-%s-%s-%s-%s-%s-%s" % (timestamp,
                                                country,
                                                group,
                                                subgroup,
                                                sentby,
                                                purpose,
                                                concept,
                                                sentto)
        # ~ self.log.debug("%s -> %s", filename, suggested)
        return suggested
