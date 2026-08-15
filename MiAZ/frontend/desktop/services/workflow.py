# File: workflow.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Workflow module

import os
from gettext import gettext as _

from gi.repository import GLib
from gi.repository import GObject

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.status import MiAZStatus
from MiAZ.backend.watcher import MiAZWatcher
from MiAZ.frontend.desktop.widgets.settings import MiAZRepoSettings


class MiAZWorkflow(GObject.GObject):
    """
    Repository workflow
    """

    __gsignals__ = {
        "repository-switch-started": (GObject.SignalFlags.RUN_LAST, None, ()),
        "repository-switch-finished": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, app):
        """
        Initialize workflow service.

        :param app: pointer to MiAZApp
        :type app: MiAZApp
        """
        super().__init__()
        self.app = app
        self.log = MiAZLog('MiAZ.Workflow')
        self.actions = self.app.get_service('actions')
        self.util = self.app.get_service('util')
        self.srvdlg = self.app.get_service('dialogs')
        self._sid_pending_docs = None
        self.log.debug("Service Workflow initialized")

    def _unload_plugins(self):
        """Take down the plugins of the repository being left.

        The enabled set is per repository (plugins-used.json lives in the
        repository .conf), so a switch has to unload before it loads: without
        this the second repository kept the first one's plugins and ignored its
        own list. Clearing the loaded flag is what lets app.load_plugins() run
        again for the repository being opened.
        """
        plugin_manager = self.app.get_service('plugin-system')
        if plugin_manager is None:
            # Startup: the plugin system is registered after the first switch.
            return
        plugin_manager.unload_all()
        self.app.set_plugins_loaded(False)

    def switch_start(self, *args, repo_id=None):
        """Switch from one repository to another, in place.

        With no repo_id the default repository ('current') is loaded, which is
        what happens at startup. Passing repo_id opens that repository without
        touching 'current', so the user can look at another one without
        changing what MiAZ opens next time. Writing the default is the caller's
        decision, taken before calling here.

        Returns whether a repository ended up loaded.
        """
        self.log.debug(f"Repository switch requested (repo_id={repo_id})")
        repository = self.app.get_service('repo')

        # Resolve the target before anything is torn down: an unknown id must
        # leave the repository on screen exactly as it was.
        if repo_id is not None:
            config_repos = self.app.get_config('Repository')
            if config_repos is None or not config_repos.get_path(repo_id, used=True):
                self.log.error(f"Repository '{repo_id}' is not one of the repositories in use")
                return False

        self.emit("repository-switch-started")

        # The enabled plugin set lives in the repository being left, so its
        # plugins go before the new configuration replaces it. Their teardown
        # runs while their own repository is still the current one.
        self._unload_plugins()

        if repo_id is not None:
            repository.use(repo_id=repo_id)
        else:
            repository.reset()
        try:
            self.app.set_status(MiAZStatus.BUSY)
            repo_loaded = False
            if repository.validate(repository.docs):
                repository.load(repository.docs)
                repo_loaded = True
        except Exception as error:
            self.log.error(error)
            repo_loaded = False

        active_id = repository.get_active_id()
        self.log.debug(f"Repository '{active_id}' loaded? {repo_loaded}")
        self.log.debug(f"Repository error: {repository.get_error()}")

        window = self.app.get_widget('window')
        window.present()
        sidebar = self.app.get_widget('sidebar')
        if repo_loaded:
            self.log.info(f"Repo Working directory: '{repository.docs}'")
            # Built against the repository being opened. The one from the
            # previous repository shows that repository's vocabularies, so it
            # is replaced rather than reused, and closed if it was on screen.
            previous = self.app.get_widget('settings-repo')
            if previous is not None:
                previous.close()
            self.app.add_widget('settings-repo', MiAZRepoSettings(self.app))
            workspace = self.app.get_widget('workspace')
            workspace.initialize_caches()
            tgbPendingDocs = self.app.get_widget('workspace-togglebutton-pending-docs')
            if self._sid_pending_docs is None:
                # Connected once for the life of the button. Connecting on
                # every switch left one handler per switch, so the pending
                # filter ran as many times as repositories had been opened.
                self._sid_pending_docs = tgbPendingDocs.connect(
                    'toggled', workspace.show_pending_documents)
            if not self.app.get_plugins_loaded():
                self.app.load_plugins()
            self.app.set_status(MiAZStatus.RUNNING)
            workspace.emit('workspace-view-filtered')
            sidebar.set_visible(True)
            self.actions.show_stack_page_by_name('workspace')
            self.app.emit('application-started')
            GLib.idle_add(self._check_repo_config)
        else:
            self.app.set_status(MiAZStatus.RUNNING)
            self.actions.show_stack_page_by_name('welcome')
            sidebar.set_visible(False)
            self._maybe_launch_assistant()
            GLib.idle_add(self._report_load_failure, repository, active_id)

        return repo_loaded

    def _report_load_failure(self, repository, repo_id):
        """Say why the configured repository could not be opened.

        Silence here was the worst case in the app: a repository directory that
        had been renamed, deleted or left on an unmounted drive took the user
        to the welcome page with no explanation, and the repository looked
        empty rather than absent. Runs on idle so the window is up first.

        Nothing is said when no repository is configured at all: that is a
        first run, and the assistant is already on screen.
        """
        repos_cfg = self.app.get_config('Repository')
        if repos_cfg is None or not repos_cfg.load_used():
            return False

        path = repos_cfg.get_path(repo_id, used=True) if repo_id else ''
        title = _('Repository management')
        body = _('The repository <b>{repository}</b> could not be opened.').format(
            repository=repo_id or _('configured'))
        if path and not os.path.isdir(path):
            body += '\n\n' + _('Its directory no longer exists:')
            body += f'\n<tt>{path}</tt>'
            body += '\n\n' + _('It may have been renamed or moved, or it may be '
                               'on a drive that is not connected. MiAZ has not '
                               'changed anything. Reconnect it, or point the '
                               'repository somewhere else in Settings, '
                               'Repositories.')
        else:
            detail = repository.get_error()
            if detail:
                body += '\n\n' + str(detail)

        parent = self.app.get_widget('window')
        self.srvdlg.show_error(title=title, body=body, parent=parent, width=480)
        return False

    def _maybe_launch_assistant(self):
        """On a fresh install (no repository configured at all), open the
        first-run assistant on top of the welcome page. If a repository is
        configured but failed to load, keep the welcome page so the existing
        setup is not shadowed.
        """
        repos_cfg = self.app.get_config('Repository')
        has_repo = repos_cfg is not None and len(repos_cfg.load_used()) > 0
        if has_repo:
            return
        if self.app.get_widget('window-repo-assistant') is not None:
            return
        self.actions.show_repository_assistant()

    def _check_repo_config(self):
        """Open Repository Management if any required config section has no used items."""
        required = ('Country', 'Group', 'SentBy', 'Purpose', 'SentTo', 'Plugin')
        missing = None
        for key in required:
            config = self.app.get_config(key)
            if config is not None and not config.load_used():
                missing = key
                break
        if missing is None:
            return False
        message = f"Repository config for '{missing}' has no used entries: open settings dialog"
        self.log.warning(message)
        repo_settings = self.app.get_widget('settings-repo')
        if repo_settings is None:
            self.log.error("settings-repo widget not found; cannot auto-open repository settings")
            return False
        window_main = self.app.get_widget('window')
        try:
            repo_settings.set_transient_for(window_main)
            repo_settings.set_modal(True)
            repo_settings.present()
        except Exception as error:
            self.log.error(f"Failed to present repository settings: {error}")
        return False

    def switch_finish(self, *args):
        """Finish switch repository operation"""
        repository = self.app.get_service('repo')
        remote = self.util.is_remote_path(repository.docs)
        if remote:
            success, error = self.util.check_remote_directory_sync(repository.docs)
        else:
            success = True
            error = None

        if success:
            self.log.info(f"Remote directory '{repository.docs}' is available.")
        else:
            self.log.info(f"Remote directory '{repository.docs}' is NOT available. Reason: {error}")
            return

        # Re-point the existing watcher rather than building another one. The
        # workspace connects to the watcher service once, when it is built, so
        # replacing the object left it listening to a deactivated watcher: after
        # the first repository switch, files added or removed outside the app
        # stopped reaching the view until a restart. set_path() rebuilds the
        # file monitor for the new directory, which is all that has to change.
        watcher = self.app.get_service('watcher')
        if watcher is None:
            watcher = MiAZWatcher(dirpath=repository.docs, remote=remote)
            self.app.set_service('watcher', watcher)
        else:
            watcher.set_active(False)
            watcher.remote = remote
            watcher.set_path(repository.docs)
        watcher.set_active(active=True)
        self.log.debug("Repository switch finished")

        # Setup stack pages
        mainbox = self.app.get_widget('window-mainbox')
        page_workspace = self.app.get_widget('workspace')
        if page_workspace is None:
            mainbox._setup_page_workspace()

        headerbar = self.app.get_widget('headerbar')
        headerbar.set_visible(True)
        btnWorkspace = self.app.get_widget('workspace-menu')
        if btnWorkspace is not None:
            btnWorkspace.set_visible(True)
        switcher = self.app.get_widget('workspace-view-switcher')
        if switcher is not None:
            switcher.set_visible(True)

        self.emit("repository-switch-finished")
