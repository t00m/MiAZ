#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from os.path import basename
import shutil

from gi.repository import GObject

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.backend.util import MiAZUtil
# ~ from MiAZ.backend.util import json_load, json_save
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
    s_repodct = {}
    util = None
    checking = False

    def __init__(self) -> None:
        GObject.GObject.__init__(self)
        self.log = get_logger('MiAZBackend')
        GObject.signal_new('source-configuration-updated',
                            MiAZBackend,
                            GObject.SignalFlags.RUN_LAST, None, () )
        self.util = MiAZUtil(self)
        self.conf['App'] = MiAZConfigApp(self)

    def repo_validate(self, path: str) -> bool:
        self.log.debug("Checking conf dir: %s", path)
        conf_dir = os.path.join(path, '.conf')
        conf_file = os.path.join(conf_dir, 'repo.json')
        if os.path.exists(conf_dir):
            self.log.debug("Config path '%s' exists", conf_dir)
            if os.path.exists(conf_file):
                repo = self.util.json_load(conf_file)
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
        self.util.json_save(conf_file, conf)
        self.conf['App'].set('source', path)
        self.log.debug("Repo configuration initialized")

    def repo_config(self):
        conf = {}
        conf['dir_docs'] = self.conf['App'].get('source')
        conf['dir_conf'] = os.path.join(conf['dir_docs'], '.conf')
        conf['cnf_file'] = os.path.join(conf['dir_conf'], "docs.json" )
        conf['dct_repo'] = self.s_repodct
        return conf

    def repo_load(self, path):
        conf = self.repo_config()
        dir_conf = conf['dir_conf']
        self.conf['Country'] = MiAZConfigSettingsCountries(self, dir_conf)
        self.conf['Country'].connect('repo-settings-updated-countries-used', self.repo_check)
        self.conf['Group'] = MiAZConfigSettingsGroups(self, dir_conf)
        self.conf['Group'].connect('repo-settings-updated-groups-used', self.repo_check)
        self.conf['Subgroup'] = MiAZConfigSettingsSubgroups(self, dir_conf)
        self.conf['Purpose'] = MiAZConfigSettingsPurposes(self, dir_conf)
        self.conf['Concept'] = MiAZConfigSettingsConcepts(self, dir_conf)
        self.conf['SentBy'] = MiAZConfigSettingsSentBy(self, dir_conf)
        self.conf['SentTo'] = MiAZConfigSettingsSentTo(self, dir_conf)
        self.conf['Person'] = MiAZConfigSettingsPeople(self, dir_conf)
        self.watcher = MiAZWatcher('source', path)
        self.watcher.set_active(active=True)
        self.watcher.connect('repository-updated', self.repo_check)
        # ~ self.conf['App'].connect('repo-settings-updated-app', self.foo)
        self.log.debug("Configuration loaded")

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
        try:
            self.s_repodct = self.util.json_load(s_repocnf)
            self.log.debug("Loaded configuration from: %s" % s_repocnf)
        except FileNotFoundError:
            self.s_repodct = {}
            self.util.json_save(s_repocnf, self.s_repodct)
            self.log.debug("Created an empty configuration file in: %s" % s_repocnf)

        # Workflow
        # 1. Check and delete inconsistencies.
        for doc in self.s_repodct.copy():
            if not os.path.exists(doc):
                del(self.s_repodct[doc])
                self.log.debug("File[%s] - Inconistency found. Deleted"
                                                        % basename(doc))

        # 2. Rebuild repository dictionary
        docs = self.util.get_files(s_repodir)
        for doc in docs:
            valid, reasons = self.util.validate_filename(doc)
            self.s_repodct[doc] = {}
            self.s_repodct[doc]['valid'] = valid
            self.s_repodct[doc]['reasons'] = reasons
            self.s_repodct[doc]['suggested'] = None
            self.s_repodct[doc]['fields'] = self.util.get_fields(doc)
        self.log.info("Repository check finished: %d documents analyzed", len(docs))
        self.util.json_save(s_repocnf, self.s_repodct)

        # 3. Emit the 'source-configuration-updated' signal
        self.log.debug("Source repository updated")
        self.emit('source-configuration-updated')
        self.checking = False
