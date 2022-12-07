#!/usr/bin/env python
# -*- coding: utf-8 -*-

from MiAZ.backend.log import get_logger

class MiAZRepoManager:
    """Manage document repositories"""

    def __init__(self, app):
        self.app = app
        self.conf = self.app.get_conf()
        self.log = get_logger("MiAZ.Backend.Repository")
        self.log.debug("Initializing repository subsystem")
        self.log.debug("Number of repos: %d", len(self.get_repos()))
        self.log.debug("Last repo used: %s", self.get_current())

    def add(self, name: str, path: str) -> bool:
        """Add a new repository
        Check if already exist one with that name or path.
        """
        if self.get_repo_by_name(name):
            repo_path = self.get_repo_path_by_name(name)
            self.log.debug("Repo with name '%s' already used (using path %s)", name, repo_path)

        if self.get_repo_by_path(path):
            repo_name = self.get_repo_name_by_path(name)
            self.log.debug("Repo with path '%s' already used (using name %s)", path, repo_name)


    def exists(self, name: str) -> bool:

        return True

    def get_repo_path_by_name(self, name: str) -> str:
        try:
            path = self._repos[name]
        except KeyError:
            path = None
        return path

    def get_repo_name_by_path(self, path: str) -> str:
        try:
            name = list(self._repos.keys())[list(self._repos.values()).index(path)]
        except ValueError:
            name = None
        return name

    def get_current(self):
        return self.conf['App'].get('current')

    def get_repos(self):
        return self.conf['App'].get('repos')

    def switch(self, name):
        repos = self.get_repos()
        current = self.get_current()
        path = repos[current]
        self.repo = {}
        self.repo['path'] = path
        self.repo['conf'] = os.path.join(path, 'conf')
        self.repo['meta'] = os.path.join(path, 'meta')
        self.repo['proj'] = os.path.join(path, 'proj')
        self.repo['repo'] = os.path.join(path, 'repo')
        self.repo['tags'] = os.path.join(path, 'tags')


