#!/usr/bin/python3

"""
# File: repository.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Repository documents module
"""

import os
import json
from gettext import gettext as _

from gi.repository import GObject

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.config import MiAZConfigCountries
from MiAZ.backend.config import MiAZConfigGroups
from MiAZ.backend.config import MiAZConfigPurposes
from MiAZ.backend.config import MiAZConfigConcepts
from MiAZ.backend.config import MiAZConfigPeople
from MiAZ.backend.config import MiAZConfigSentBy
from MiAZ.backend.config import MiAZConfigSentTo
from MiAZ.backend.config import MiAZConfigUserPlugins


class MiAZRepository(GObject.GObject):
    __gtype_name__ = 'MiAZRepository'
    _errmsg = None

    def __init__(self, app):
        sid = GObject.signal_lookup('repository-switched', MiAZRepository)
        if sid == 0:
            super().__init__()
            GObject.signal_new('repository-switched',
                                MiAZRepository,
                                GObject.SignalFlags.RUN_LAST, None, ())
        self.app = app
        self.log = MiAZLog('MiAZ.Repository')
        self.config = self.app.get_config_dict()
        self.log.info("Repository class initialited")

    @property
    def docs(self):
        """Repository documents directory"""
        return self.get('dir_docs')

    @property
    def conf(self):
        """Repository configuration directory"""
        return self.get('dir_conf')

    def validate(self, path: str) -> bool:
        valid = False
        try:
            conf_dir = os.path.join(path, '.conf')
            conf_file = os.path.join(conf_dir, 'repo.json')
            self.log.debug(f"Validating repository '{conf_file}'")
            if os.path.exists(conf_dir):
                if os.path.exists(conf_file):
                    with open(conf_file, 'r') as fin:
                        try:
                            json.load(fin)
                            valid = True
                        except Exception as error:
                            self.log.error(error)
            self.log.debug(f"Repository {conf_file} valid? {valid}")
        except Exception as error:
            errmsg = _("No repositories found.")

            errmsg = _("Please, create a new repository, if none exists yet.\n\n")
            errmsg += _("Otherwise, check if the directory exists (local repository) or if the server is accessible (remote repository).")
            # ~ errmsg += _("Exception error: {error}\n\n").format(error=error)
            # ~ errmsg += _("Repository path '{path}' not valid.\n").format(path=path)
            self.log.error(errmsg)
            self.set_error(errmsg)
        return valid

    def init(self, path):
        repoconf = {}
        repoconf['FORMAT'] = 1
        dir_conf = os.path.join(path, '.conf')
        os.makedirs(dir_conf, exist_ok=True)
        conf_file = os.path.join(dir_conf, 'repo.json')
        with open(conf_file, 'w') as fout:
            json.dump(repoconf, fout, sort_keys=True, indent=4)
        self.config['App'].set('source', path)
        self.log.debug(f"Repository initialited: '{conf_file}'")

    def setup(self, repo_id: str = None):
        conf = {}
        # ~ self.log.debug(f"Repo Id: {repo_id}")
        if repo_id is None:
            # Try to load the default repository
            # ~ self.log.debug("Loading current repository from config")
            repo_id = self.config['App'].get('current')
            # ~ self.log.debug(f"Config has repo: {repo_id}")
            if repo_id is None:
                self.log.warning("No repository configuration available")
        if repo_id is not None:
            repos_used = self.config['Repository'].load_used()
            # ~ self.log.debug(f"Number of repositories in use: {len(repos_used)}")
            if len(repos_used) > 0:
                try:
                    repo_path = repos_used[repo_id]
                    conf['dir_docs'] = repo_path
                    conf['dir_conf'] = os.path.join(conf['dir_docs'], '.conf')
                    if not os.path.exists(conf['dir_conf']):
                        self.init(conf['dir_docs'])
                except Exception as error:
                    self.set_error(error)
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
        self.config['Plugin'] = MiAZConfigUserPlugins(self.app, repo_dir_conf)
        self.log.debug(f"Repository configuration loaded correctly from: {repo_dir_conf}")
        self.emit('repository-switched')

    def get(self, key: str) -> str:
        try:
            repoconf = self.setup()
            return repoconf[key]
        except Exception as error:
            self.log.warning(f"Repository Configuration Key '{key}' not found")

    def get_error(self):
        return self._errmsg

    def set_error(self, msg):
        """Last repository error"""
        self._errmsg = msg
