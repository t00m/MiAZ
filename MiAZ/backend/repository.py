#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: repository.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Allow (un)assign documentos from/to projects
"""

import os
import json

from gi.repository import GObject

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.config import MiAZConfigCountries
from MiAZ.backend.config import MiAZConfigGroups
from MiAZ.backend.config import MiAZConfigProjects
from MiAZ.backend.config import MiAZConfigPurposes
from MiAZ.backend.config import MiAZConfigConcepts
from MiAZ.backend.config import MiAZConfigPeople
from MiAZ.backend.config import MiAZConfigSentBy
from MiAZ.backend.config import MiAZConfigSentTo

from MiAZ.backend.config import MiAZConfigUserPlugins
from MiAZ.backend.watcher import MiAZWatcher
from MiAZ.backend.projects import MiAZProject
from MiAZ.backend.util import HERE


class MiAZRepository(GObject.GObject):
    __gtype_name__ = 'MiAZRepository'

    def __init__(self, app):
        sid = GObject.signal_lookup('repository-switched', MiAZRepository)
        if sid == 0:
            super(MiAZRepository, self).__init__()
            GObject.signal_new('repository-switched',
                                MiAZRepository,
                                GObject.SignalFlags.RUN_LAST, None, () )
        self.app = app
        self.log = MiAZLog('MiAZ.Repository')
        self.config = self.app.get_config_dict()
        self.log.debug(self.config)

    @property
    def docs(self):
        """Repository documents directory"""
        return self.get('dir_docs')

    @property
    def conf(self):
        """Repository documents directory"""
        return self.get('dir_conf')

    def validate(self, path: str) -> bool:
        conf_dir = os.path.join(path, '.conf')
        conf_file = os.path.join(conf_dir, 'repo.json')
        self.log.debug("Validating repository '%s'", conf_file)
        valid = False
        if os.path.exists(conf_dir):
            if os.path.exists(conf_file):
                with open(conf_file, 'r') as fin:
                    try:
                        repo = json.load(fin)
                        valid = True
                    except Exception as error:
                        self.log.error(error)
        self.log.debug("MiAZ Repository valid? %s", valid)
        return valid

    def init(self, path):
        repoconf = {}
        repoconf['FORMAT'] = 1
        dir_conf = os.path.join(path, '.conf')
        os.makedirs(dir_conf, exist_ok = True)
        conf_file = os.path.join(dir_conf, 'repo.json')
        with open(conf_file, 'w') as fout:
            json.dump(repoconf, fout, sort_keys=True, indent=4)
        self.config['App'].set('source', path)
        self.log.debug("Repository initialited: '%s'", conf_file)

    def setup(self, repo_id: str = None):
        repos_used = self.config['Repository'].load_used()
        if repo_id is None:
            repo_id = self.config['App'].get('current')
        try:
            repo_path = repos_used[repo_id]
            conf = {}
            conf['dir_docs'] = repo_path
            conf['dir_conf'] = os.path.join(conf['dir_docs'], '.conf')
            if not os.path.exists(conf['dir_conf']):
                self.init(conf['dir_docs'])
        except Exception as warning:
            self.log.warning("Repository configuration couldn't be loaded for repo_id '%s'", repo_id)
            conf = {}
        return conf

    def load(self, path):
        repo_dir_conf = self.get('dir_conf')
        self.config['Country'] = MiAZConfigCountries(self.app, repo_dir_conf)
        self.config['Group'] = MiAZConfigGroups(self.app, repo_dir_conf)
        self.config['Purpose'] = MiAZConfigPurposes(self.app, repo_dir_conf)
        self.config['Concept'] = MiAZConfigConcepts(self.app, repo_dir_conf)
        self.config['SentBy'] = MiAZConfigSentBy(self.app, repo_dir_conf)
        self.config['SentTo'] = MiAZConfigSentTo(self.app, repo_dir_conf)
        self.config['Person'] = MiAZConfigPeople(self.app, repo_dir_conf)
        self.config['Project'] = MiAZConfigProjects(self.app, repo_dir_conf)
        self.config['Plugin'] = MiAZConfigUserPlugins(self.app, repo_dir_conf)
        self.app.add_service('Projects', MiAZProject(self.app))
        watcher = MiAZWatcher(path)
        watcher.set_active(active=True)
        self.app.add_service('watcher', watcher)
        self.log.debug("Repository configuration loaded correctly from: %s", repo_dir_conf)
        self.emit('repository-switched')

    def get(self, key: str) -> str:
        repoconf = self.setup()
        return repoconf[key]
