#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: __init__.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Backend Package initialization
"""

import os

from gi.repository import GObject

from MiAZ.backend.log import get_logger
from MiAZ.backend.util import MiAZUtil
from MiAZ.backend.watcher import MiAZWatcher
from MiAZ.backend.projects import MiAZProject
from MiAZ.backend.config import MiAZConfigApp
from MiAZ.backend.config import MiAZConfigCountries
from MiAZ.backend.config import MiAZConfigGroups
from MiAZ.backend.config import MiAZConfigProjects
from MiAZ.backend.config import MiAZConfigPurposes
from MiAZ.backend.config import MiAZConfigConcepts
from MiAZ.backend.config import MiAZConfigPeople
from MiAZ.backend.config import MiAZConfigSentBy
from MiAZ.backend.config import MiAZConfigSentTo
from MiAZ.backend.config import MiAZConfigRepositories


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
        self.util = MiAZUtil(self)
        self.conf['App'] = MiAZConfigApp(self)
        self.conf['Repository'] = MiAZConfigRepositories(self)

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
        repo_id = self.conf['App'].get('current')
        repos_used = self.conf['Repository'].load_used()
        try:
            repo_path = repos_used[repo_id]
            conf = {}
            conf['dir_docs'] = repo_path
            conf['dir_conf'] = os.path.join(conf['dir_docs'], '.conf')
            if not os.path.exists(conf['dir_conf']):
                self.repo_init(conf['dir_docs'])
        except KeyError:
            conf = {}
        finally:
            return conf

    def repo_load(self, path):
        conf = self.repo_config()
        dir_conf = conf['dir_conf']
        self.conf['Country'] = MiAZConfigCountries(self, dir_conf)
        self.conf['Group'] = MiAZConfigGroups(self, dir_conf)
        self.conf['Purpose'] = MiAZConfigPurposes(self, dir_conf)
        self.conf['Concept'] = MiAZConfigConcepts(self, dir_conf)
        self.conf['SentBy'] = MiAZConfigSentBy(self, dir_conf)
        self.conf['SentTo'] = MiAZConfigSentTo(self, dir_conf)
        self.conf['Person'] = MiAZConfigPeople(self, dir_conf)
        self.conf['Project'] = MiAZConfigProjects(self, dir_conf)
        self.watcher = MiAZWatcher('source', path)
        self.watcher.set_active(active=True)
        self.watcher.connect('repository-updated', self.repo_check)
        self.projects = MiAZProject(self)
        # ~ self.conf['App'].connect('repo-settings-updated-app', self.foo)
        self.log.debug("Configuration loaded")

    def repo_check(self, *args):
        self.log.debug("Source repository updated")
        self.emit('source-configuration-updated')
