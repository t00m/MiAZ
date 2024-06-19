#!/usr/bin/python3

"""
# File: projects.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Allow (un)assign documentos from/to projects
"""

import os

from gi.repository import GObject

from MiAZ.backend.log import MiAZLog


class MiAZProject(GObject.GObject):
    """
    C0115: Missing class docstring (missing-class-docstring)
    """
    __gtype_name__ = 'MiAZProject'

    def __init__(self, app):
        """
        C0116: Missing function or method docstring (missing-function-docstring)
        """
        super().__init__()
        self.log = MiAZLog('MiAZ.Projects')
        self.app = app
        conf = self.app.get_config_dict()
        self.config = conf['Project']
        repository = self.app.get_service('repo')
        repo_dir_conf = repository.get('dir_conf')
        self.cnfprj = os.path.join(repo_dir_conf, 'projects.json')
        self.projects = {}
        if not os.path.exists(self.cnfprj):
            self.save()
            self.log.debug("Created new config file for projects")
        self.projects = self.load()
        self.check()

    def check(self):
        """
        C0116: Missing function or method docstring (missing-function-docstring)
        """
        repository = self.app.get_service('repo')
        to_delete = []
        for project in self.projects:
            for doc in self.docs_in_project(project):
                docpath = os.path.join(repository.docs, doc)
                if not os.path.exists(docpath):
                    to_delete.append((doc, project))
        for doc, project in to_delete:
            self.remove(project, doc)
        self.log.debug("Projects consistency checked")

    def add(self, project: str, doc: str):
        """
        C0116: Missing function or method docstring (missing-function-docstring)
        """
        try:
            docs = self.projects[project]
            if doc not in docs:
                docs.append(doc)
                self.projects[project] = docs
        except KeyError:
            self.projects[project] = [doc]
        self.log.debug(f"Added '{doc}' to project '{project}'")

    def add_batch(self, project: str, docs: list) -> None:
        """
        C0116: Missing function or method docstring (missing-function-docstring)
        """
        for doc in docs:
            self.add(project, doc)
        self.save()

    def remove(self, project: str, doc: str) -> None:
        """
        C0116: Missing function or method docstring (missing-function-docstring)
        """
        found = False
        if len(project) == 0:
            # Document was deleted, therefore delete all references in
            # any project
            for prj in self.projects:
                docs = self.projects[prj]
                if doc in docs:
                    found = True
                    docs.remove(doc)
                    self.log.debug(f"Removed '{doc}' from project '{prj}'")
                    self.projects[prj] = docs
        else:
            # Delete document for a given project
            try:
                docs = self.projects[project]
                if doc in docs:
                    found = True
                    docs.remove(doc)
                    self.log.debug(f"Removed '{doc}' from project '{project}'")
                    self.projects[project] = docs
            except KeyError:
                self.log.warning(f"Project '{project}' doesn't exist")
        if found:
            self.save()
        else:
            self.log.debug(f"Document '{doc}' does not belong to project {project}")

    def remove_batch(self, project:str, docs: list) -> None:
        """
        C0116: Missing function or method docstring (missing-function-docstring)
        """
        for doc in docs:
            self.remove(project, doc)
        self.save()

    def exists(self, project, doc):
        """
        C0116: Missing function or method docstring (missing-function-docstring)
        """
        try:
            return doc in self.projects[project]
        except KeyError:
            # Project {project} not present in projects.json
            # Config file projects.json deleted and then recreated emtpy?
            return False

    def assigned_to(self, doc):
        """
        C0116: Missing function or method docstring (missing-function-docstring)
        """
        projects = []
        for project in self.projects:
            if doc in self.projects[project]:
                projects.append(project)
        return projects

    def docs_in_project(self, project):
        """
        C0116: Missing function or method docstring (missing-function-docstring)
        """
        try:
            return self.projects[project]
        except KeyError:
            return []

    def list_all(self):
        """
        C0116: Missing function or method docstring (missing-function-docstring)
        """
        for project in self.projects:
            self.log.debug(f"Project: {project}")
            for doc in self.projects[project]:
                self.log.debug(f"\tDoc: {doc}")

    def save(self) -> None:
        """
        C0116: Missing function or method docstring (missing-function-docstring)
        """
        srvutil = self.app.get_service('util')
        srvutil.json_save(self.cnfprj, self.projects)

    def load(self) -> dict:
        """
        C0116: Missing function or method docstring (missing-function-docstring)
        """
        util = self.app.get_service('util')
        return util.json_load(self.cnfprj)

    def description(self, pid):
        """
        C0116: Missing function or method docstring (missing-function-docstring)
        """
        try:
            description = self.config.get(pid)
            if len(description) == 0:
                description = pid
        except KeyError as error:
            description = error
        return description
