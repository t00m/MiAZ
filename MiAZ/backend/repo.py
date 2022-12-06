#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Repository:
    def __init__(self, app):
        self.app = app
        self.conf = self.app.get_conf()

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


