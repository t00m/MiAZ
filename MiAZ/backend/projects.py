#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: projects.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Allow (un)assign documentos from/to projects
"""

import os

from gi.repository import GObject

from MiAZ.backend.log import get_logger


class MiAZProject(GObject.GObject):
    __gtype_name__ = 'MiAZProject'

    def __init__(self, backend):
        super(MiAZProject, self).__init__()
        self.backend = backend
        self.config = self.backend.conf['Project']
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
        self.log.debug("Added '%s' to Project '%s'", doc, project)

    def add_batch(self, project: str, docs: list) -> None:
        for doc in docs:
            self.add(project, doc)
        self.save()

    def remove(self, project: str, doc: str) -> None:
        found = False
        if len(project) == 0:
            # Document was deleted, therefore delete all references in
            # any project
            for prj in self.projects:
                docs = self.projects[prj]
                if doc in docs:
                    found = True
                    docs.remove(doc)
                    self.log.debug("Remove '%s' from Project '%s'", doc, prj)
                    self.projects[prj] = docs
        else:
            # Delete document for a given project
            try:
                docs = self.projects[project]
                if doc in docs:
                    found = True
                    docs.remove(doc)
                    self.log.debug("Remove '%s' from Project '%s'", doc, project)
                    self.projects[project] = docs
            except KeyError:
                self.log.warning("Project '%s' doesn't exist", project)
                pass
        if found:
            self.save()
        else:
            self.log.debug("Document '%s' wasn't deleted for any project '%s'", project)

    def remove_batch(self, project:str, docs: list) -> None:
        for doc in docs:
            self.remove(project, doc)
        self.save()

    def exists(self, project, doc):
        try:
            return doc in self.projects[project]
        except KeyError:
            # Project {project} not present in projects.json
            # Config file projects.json deleted and then recreated emtpy?
            return False

    def assigned_to(self, doc):
        projects = []
        for project in self.projects:
            if doc in self.projects[project]:
                projects.append(project)
        return projects

    def docs_in_project(self, project):
        try:
            return self.projects[project]
        except:
            return []

    def list_all(self):
        for project in self.projects:
            self.log.debug("Project: %s", project)
            for doc in self.projects[project]:
                self.log.debug("\tDoc: %s", doc)

    def save(self) -> None:
        self.backend.util.json_save(self.cnfprj, self.projects)

    def load(self) -> dict:
        return self.backend.util.json_load(self.cnfprj)

    def description(self, pid):
        try:
            description = self.config.get(pid)
            if len(description) == 0:
                description = pid
        except KeyError as error:
            description = error
        return description

