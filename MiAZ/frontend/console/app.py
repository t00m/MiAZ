"""
# File: app.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Headless application shell for the command line
"""

import os
from gettext import gettext as _

from gi.repository import GObject

from MiAZ.backend.config import MiAZConfigApp, MiAZConfigRepositories
from MiAZ.backend.index import MiAZDocumentIndex
from MiAZ.backend.log import MiAZLog
from MiAZ.backend.repository import MiAZRepository
from MiAZ.backend.util import MiAZUtil


class MiAZConsoleApp(GObject.GObject):
    """What the backend needs from an application, and nothing else.

    The backend asks an app object for six things: get_service, get_env,
    get_config, get_config_dict, connect, and somewhere to register services.
    This provides them and registers three services: util, repo and index. No
    factory, no dialogs, no plugin system, no window, no GTK.

    It is a GObject because util emits filename-added, filename-deleted and
    filename-renamed, which the commands that write will want to observe.
    """
    __gtype_name__ = 'MiAZConsoleApp'

    def __init__(self, env):
        super().__init__()
        self.log = MiAZLog('MiAZ.Console')
        self._env = env
        self._services = {}
        self._config = {}
        self._config['App'] = MiAZConfigApp(self)
        self._config['Repository'] = MiAZConfigRepositories(self)
        self.set_service('util', MiAZUtil(self))
        self.set_service('repo', MiAZRepository(self))

    def get_env(self):
        return self._env

    def get_config(self, name):
        return self._config.get(name)

    def get_config_dict(self):
        return self._config

    def set_service(self, name, service):
        self._services[name] = service
        return service

    def get_service(self, name):
        return self._services.get(name)

    def open_repository(self, selector=None):
        """Load a repository and register the index.

        `selector` is a registered name, a path, or None for the current one.
        Returns (0, '') or (exit code, message): 2 when the name is unknown,
        which is the user mistyping, and 3 when the repository is named but
        cannot be used, which is the environment being wrong.
        """
        repository = self.get_service('repo')
        repository.reset()

        if selector:
            if os.sep in selector or os.path.isdir(selector):
                resolved = repository.use(path=selector)
            else:
                known = sorted(self._config['Repository'].load_used())
                if selector not in known:
                    return 2, _("unknown repository '{name}'. Known: {known}").format(
                        name=selector, known=', '.join(known) or _('none'))
                resolved = repository.use(selector)
            if not resolved:
                return 3, _('cannot use repository: {name}').format(name=selector)

        docs = repository.docs
        if not docs:
            return 3, _('no repository configured; open MiAZ once or pass --repo')
        if not repository.validate(docs):
            return 3, _('not a MiAZ repository: {path}').format(path=docs)

        repository.load(docs)
        index = self.set_service('index', MiAZDocumentIndex(self))
        index.reload()
        return 0, ''
