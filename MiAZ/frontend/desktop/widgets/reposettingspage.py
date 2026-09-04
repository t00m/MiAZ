# File: reposettingspage.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: The Settings tab of the Repository Settings dialog

from gettext import gettext as _

from gi.repository import Adw

from MiAZ.backend.log import MiAZLog


class MiAZRepoSettingsPage(Adw.PreferencesPage):
    """Every per-repository setting: the repository itself, then the plugins.

    Plugin groups are built the first time this page is shown, not when the
    dialog opens. Building AutoScan's group runs SANE and building the OCR one
    shells out to tesseract, and neither is worth paying for to look at the
    Metadata tab.
    """
    __gtype_name__ = 'MiAZRepoSettingsPage'

    def __init__(self, app):
        super().__init__(title=_('Settings'),
                         icon_name='io.github.t00m.MiAZ-emblem-system-symbolic')
        self.app = app
        self.log = MiAZLog('MiAZ.RepoSettingsPage')
        self._built = False
        self._plugin_groups = []
        self._sid_plugins_updated = None
        self._build_repository_group()
        self.app.add_widget('repository-settings-page-settings', self)
        # A fresh page is built every time the dialog opens, so the signal
        # has to be picked up and let go with it, not held for the page's
        # lifetime: connecting once in __init__ leaks a handler, and a dead
        # dialog reacting to plugin changes is exactly the bug this project
        # already keeps a UI test for (test_ui_plugin_signals.py).
        self.connect('map', self._on_mapped)
        self.connect('unmap', self._on_unmapped)

    def _on_mapped(self, *args):
        if self._sid_plugins_updated is None:
            plugin_system = self.app.get_service('plugin-system')
            self._sid_plugins_updated = plugin_system.connect(
                'plugins-updated', self._on_plugins_updated)

    def _on_unmapped(self, *args):
        if self._sid_plugins_updated is not None:
            plugin_system = self.app.get_service('plugin-system')
            plugin_system.disconnect(self._sid_plugins_updated)
            self._sid_plugins_updated = None

    def is_built(self) -> bool:
        """Whether the plugin groups have been built yet."""
        return self._built

    def build_plugin_groups(self):
        """Ask every enabled plugin for its settings, once."""
        if self._built:
            return
        self._built = True
        registry = self.app.get_service('plugin-system').settings
        for category, owner, builder in registry.builders():
            try:
                group = builder()
            except Exception as error:
                # One plugin with a broken settings group must not take the
                # whole tab with it: the others are still worth showing.
                self.log.error(f"Plugin {owner} settings group: {error}")
                continue
            if group is None:
                continue
            if not group.get_title():
                group.set_title(_(category))
            self.add(group)
            self._plugin_groups.append(group)

    def _build_repository_group(self):
        repository = self.app.get_service('repo')
        config = self.app.get_config('Repository')
        repo_id = repository.get_active_id()

        group = Adw.PreferencesGroup(title=_('Repository'))
        self.add(group)

        row_name = Adw.EntryRow(title=_('Name'))
        row_name.set_text(config.get_description(repo_id, used=True) or '')
        row_name.connect('apply', self._on_name_applied)
        row_name.set_show_apply_button(True)
        group.add(row_name)
        self.app.add_widget('repository-settings-row-name', row_name)

        row_path = Adw.ActionRow(title=_('Location'))
        row_path.set_subtitle(repository.docs)
        # Read only: moving a repository is a different operation, and doing
        # it by editing a label would leave the documents behind.
        group.add(row_path)
        self.app.add_widget('repository-settings-row-location', row_path)

    def _on_name_applied(self, row):
        repository = self.app.get_service('repo')
        config = self.app.get_config('Repository')
        repo_id = repository.get_active_id()
        config.set_repo(repo_id, repository.docs, row.get_text(), used=True)

    def _on_plugins_updated(self, *args):
        """Throw the plugin groups away so the next showing rebuilds them."""
        for group in self._plugin_groups:
            self.remove(group)
        self._plugin_groups = []
        self._built = False
        if self.get_mapped():
            self.build_plugin_groups()
