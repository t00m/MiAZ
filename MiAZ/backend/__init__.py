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
    _config = {} # Dictionary holding configurations

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
        self._config['App'] = MiAZConfigApp(self)
        self._config['Repository'] = MiAZConfigRepositories(self)

    def get_config(self):
        return self._config

    def get_service(self, service: str):
        """Convenient method to get a service"""
        return self.app.get_service(service)

    def repo_validate(self, path: str) -> bool:
        srvutil = self.app.get_service('util')
        conf_dir = os.path.join(path, '.conf')
        conf_file = os.path.join(conf_dir, 'repo.json')
        valid = False
        if os.path.exists(conf_dir):
            if os.path.exists(conf_file):
                repo = srvutil.json_load(conf_file)
                valid = True
            else:
                valid = False
        else:
            valid = False
        self.log.debug("MiAZ Repository valid? %s", valid)
        return valid

    def repo_init(self, path):
        config = self.get_config()
        srvutil = self.app.get_service('util')
        repoconf = {}
        repoconf['FORMAT'] = 1
        dir_conf = os.path.join(path, '.conf')
        os.makedirs(dir_conf, exist_ok = True)
        conf_file = os.path.join(dir_conf, 'repo.json')
        srvutil.json_save(conf_file, repoconf)
        self.log.debug("Repository config file saved: '%s'", conf_file)
        config['App'].set('source', path)
        self.log.debug("Repo configuration initialized")

    def repo_config(self, repo_id: str = None):
        config = self.get_config()
        repos_used = config['Repository'].load_used()

        if repo_id is None:
            repo_id = config['App'].get('current')
            # ~ self.log.debug("Using default repository (%s) from configuration", repo_id)
        # ~ else:
            # ~ self.log.debug("Using repo '%s'", repo_id)

        try:
            repo_path = repos_used[repo_id]
            conf = {}
            conf['dir_docs'] = repo_path
            conf['dir_conf'] = os.path.join(conf['dir_docs'], '.conf')
            if not os.path.exists(conf['dir_conf']):
                self.repo_init(conf['dir_docs'])
        except Exception as error:
            self.log.error(error)
            conf = {}
        return conf

    def repo_load(self, path):
        repoconf = self.repo_config()
        dir_conf = repoconf['dir_conf']
        self._config['Country'] = MiAZConfigCountries(self, dir_conf)
        self._config['Group'] = MiAZConfigGroups(self, dir_conf)
        self._config['Purpose'] = MiAZConfigPurposes(self, dir_conf)
        self._config['Concept'] = MiAZConfigConcepts(self, dir_conf)
        self._config['SentBy'] = MiAZConfigSentBy(self, dir_conf)
        self._config['SentTo'] = MiAZConfigSentTo(self, dir_conf)
        self._config['Person'] = MiAZConfigPeople(self, dir_conf)
        self._config['Project'] = MiAZConfigProjects(self, dir_conf)
        self._config['Plugin'] = MiAZConfigUserPlugins(self, dir_conf)
        # ~ for cid in self._config:
            # ~ self.log.debug("\tConfig for %s: %d values", cid, len(self._config[cid].load_used()))
        self.watcher = MiAZWatcher('source', path)
        self.watcher.set_active(active=True)
        self.watcher.connect('repository-updated', self.repo_check)
        self.projects = MiAZProject(self)
        self.log.debug("Config repo loaded from: %s", dir_conf)
        self.emit('repository-switched')

    def repo_check(self, *args):
        self.log.debug("Source repository updated")
        self.emit('repository-updated')
