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

from MiAZ.backend.log import get_logger
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


class MiAZRepository(GObject.GObject):
    __gtype_name__ = 'MiAZRepository'

    def __init__(self, backend):
        super(MiAZRepository, self).__init__()
        GObject.signal_new('repository-switched',
                            MiAZRepository,
                            GObject.SignalFlags.RUN_LAST, None, () )
        self.log = get_logger('MiAZRepo')
        self.backend = backend
        # ~ self.util = self.backend.get_service('util')
        self.config = self.backend.get_config()
        self.log.debug(self.config)

    def json_load(self, filepath: str) -> {}:
        """Load into a dictionary a file in json format"""
        with open(filepath, 'r') as fin:
            adict = json.load(fin)
        return adict

    def json_save(self, filepath: str, adict: {}) -> {}:
        """Save dictionary into a file in json format"""
        with open(filepath, 'w') as fout:
            json.dump(adict, fout, sort_keys=True, indent=4)

    def validate(self, path: str) -> bool:
        conf_dir = os.path.join(path, '.conf')
        conf_file = os.path.join(conf_dir, 'repo.json')
        valid = False
        if os.path.exists(conf_dir):
            if os.path.exists(conf_file):
                repo = self.json_load(conf_file)
                valid = True
            else:
                valid = False
        else:
            valid = False
        self.log.debug("MiAZ Repository valid? %s", valid)
        return valid

    def init(self, path):
        # ~ config = self.get_config()
        repoconf = {}
        repoconf['FORMAT'] = 1
        dir_conf = os.path.join(path, '.conf')
        os.makedirs(dir_conf, exist_ok = True)
        conf_file = os.path.join(dir_conf, 'repo.json')
        self.json_save(conf_file, repoconf)
        self.log.debug("Repository config file saved: '%s'", conf_file)
        self.config['App'].set('source', path)
        self.log.debug("Repo configuration initialized")

    def setup(self, repo_id: str = None):
        # ~ config = self.get_config()
        repos_used = self.config['Repository'].load_used()

        if repo_id is None:
            repo_id = self.config['App'].get('current')

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

    def load(self, path):
        repoconf = self.setup()
        dir_conf = repoconf['dir_conf']
        self.config['Country'] = MiAZConfigCountries(self.backend, dir_conf)
        self.config['Group'] = MiAZConfigGroups(self.backend, dir_conf)
        self.config['Purpose'] = MiAZConfigPurposes(self.backend, dir_conf)
        self.config['Concept'] = MiAZConfigConcepts(self.backend, dir_conf)
        self.config['SentBy'] = MiAZConfigSentBy(self.backend, dir_conf)
        self.config['SentTo'] = MiAZConfigSentTo(self.backend, dir_conf)
        self.config['Person'] = MiAZConfigPeople(self.backend, dir_conf)
        self.config['Project'] = MiAZConfigProjects(self.backend, dir_conf)
        self.config['Plugin'] = MiAZConfigUserPlugins(self.backend, dir_conf)
        self.backend.add_service('Projects', MiAZProject(self.backend))
        watcher = self.backend.add_service('watcher', MiAZWatcher('source', path))
        watcher.set_active(active=True)
        self.log.debug("Config repo loaded from: %s", dir_conf)
        self.emit('repository-switched')

