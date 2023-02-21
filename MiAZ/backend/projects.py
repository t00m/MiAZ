#!/usr/bin/env python
import os

from gi.repository import GObject

from MiAZ.backend.log import get_logger


class MiAZProject(GObject.GObject):
    __gtype_name__ = 'MiAZProject'

    def __init__(self, backend):
        super(MiAZProject, self).__init__()
        self.backend = backend
        self.log = get_logger('MiAZProject')
        repo = self.backend.repo_config()
        self.cnfprj = os.path.join(repo['dir_conf'], 'projects.json')
        self.projects = {}
        if not os.path.exists(self.cnfprj):
            self.save()
            self.log.debug("Created new config file for projects")
        self.projects = self.load()

    def add(self, project: str, doc: str):
        try:
            docs = self.projects[project]
            if not doc in docs:
                docs.append(doc)
                self.projects[project] = docs
        except:
            self.projects[project] = [doc]
        self.log.debug("Added %s to Project %s", doc, project)

    def add_batch(self, project: str, docs: list) -> None:
        for doc in docs:
            self.add(project, doc)
        self.save()

    def remove(self, project: str, doc: str) -> None:
        try:
            docs = self.projects[project]
            if doc in docs:
                docs.remove(doc)
            self.projects[project] = docs
        except KeyError:
            pass

    def remove_batch(self, project:str, docs: list) -> None:
        for doc in docs:
            self.remove(project, doc)
        self.save()

    def exists(self, project, doc):
        return doc in self.projects[project]

    def assigned_to(self, doc):
        projects = []
        for project in self.projects:
            if doc in self.projects[project]:
                projects.append(project)
        return projects

    def list_all(self):
        for project in self.projects:
            self.log.debug("Project: %s", project)
            for doc in self.projects[project]:
                self.log.debug("\tDoc: %s", doc)

    def save(self) -> None:
        self.backend.util.json_save(self.cnfprj, self.projects)

    def load(self) -> dict:
        return self.backend.util.json_load(self.cnfprj)


