#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: __init__.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Backend Package initialization
"""

import os

import gi
from gi.repository import GObject

from MiAZ.backend.log import get_logger
from MiAZ.backend.util import MiAZUtil
from MiAZ.backend.watcher import MiAZWatcher
from MiAZ.backend.stats import MiAZStats
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
from MiAZ.backend.config import MiAZConfigUserPlugins

class MiAZBackend(GObject.GObject):
    """Backend class"""
    __gtype_name__ = 'MiAZBackend'
    _conf = {} # Dictionary holding configuration for app and repository

    def __init__(self, app) -> None:
        GObject.GObject.__init__(self)
        self.app = app
        self.log = get_logger('MiAZBackend')
        GObject.signal_new('repository-updated',
                            MiAZBackend,
                            GObject.SignalFlags.RUN_LAST, None, () )
        GObject.signal_new('repository-switched',
                            MiAZBackend,
                            GObject.SignalFlags.RUN_LAST, None, () )

        self.app.add_service('util', MiAZUtil(self))
        self.app.add_service('stats', MiAZStats(self))
        self._conf['App'] = MiAZConfigApp(self)
        self._conf['Repository'] = MiAZConfigRepositories(self)

    def get_conf(self):
        return self._conf

    def get_service(self, service: str):
        """Convenient method to get a service"""
        return self.app.get_service(service)

    def repo_validate(self, path: str) -> bool:
        srvutil = self.app.get_service('util')
        conf_dir = os.path.join(path, '.conf')
        conf_file = os.path.join(conf_dir, 'repo.json')
        if os.path.exists(conf_dir):
            self.log.debug("Config path '%s' exists", conf_dir)
            if os.path.exists(conf_file):
                repo = srvutil.json_load(conf_file)
                self.log.debug("Current repository: %s", path)
                # ~ self.log.debug("MiAZ Repository format: %s", repo['FORMAT'])
                return True
            else:
                self.log.debug("Repo config file '%s' doesn't exist", conf_file)
                return True
        else:
            self.log.debug("Config dir '%s' doesn't exist", conf_dir)
            return False

    def repo_init(self, path):
        srvutil = self.app.get_service('util')
        conf = {}
        conf['FORMAT'] = 1
        dir_conf = os.path.join(path, '.conf')
        os.makedirs(dir_conf, exist_ok = True)
        conf_file = os.path.join(dir_conf, 'repo.json')
        srvutil.json_save(conf_file, conf)
        self.conf['App'].set('source', path)
        self.log.debug("Repo configuration initialized")

    def repo_config(self):
        config = self.get_conf()
        repo_id = config['App'].get('current')
        repos_used = config['Repository'].load_used()
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
        repoconf = self.repo_config()
        dir_conf = repoconf['dir_conf']
        self.log.debug("Loading config repo from: %s", dir_conf)
        self._conf['Country'] = MiAZConfigCountries(self, dir_conf)
        self._conf['Group'] = MiAZConfigGroups(self, dir_conf)
        self._conf['Purpose'] = MiAZConfigPurposes(self, dir_conf)
        self._conf['Concept'] = MiAZConfigConcepts(self, dir_conf)
        self._conf['SentBy'] = MiAZConfigSentBy(self, dir_conf)
        self._conf['SentTo'] = MiAZConfigSentTo(self, dir_conf)
        self._conf['Person'] = MiAZConfigPeople(self, dir_conf)
        self._conf['Project'] = MiAZConfigProjects(self, dir_conf)
        self._conf['Plugin'] = MiAZConfigUserPlugins(self, dir_conf)
        for cid in self._conf:
            self.log.debug("\tConfig for %s: %d values", cid, len(self._conf[cid].load_used()))
        self.watcher = MiAZWatcher('source', path)
        self.watcher.set_active(active=True)
        self.watcher.connect('repository-updated', self.repo_check)
        self.projects = MiAZProject(self)
        self.log.debug("Configuration loaded")
        self.emit('repository-switched')

    def repo_check(self, *args):
        self.log.debug("Source repository updated")
        self.emit('repository-updated')
