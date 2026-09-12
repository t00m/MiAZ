# File: reposettingspage.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: The Settings tab of the Repository Settings dialog

from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog
from MiAZ.frontend.desktop.widgets.sidebarstack import MiAZSidebarStack

# The page every repository has, whatever plugins are enabled. Kept apart from
# the plugin pages because it is never thrown away and rebuilt.
REPOSITORY_PAGE = 'Repository-self'

# The plugin category whose groups belong on that same page. MiAZDoctor and
# MiAZHistory file themselves under it, and giving it a page of its own put a
# second entry titled 'Repository' in the list, directly under the first, with
# nothing to tell the user which was which.
REPOSITORY_CATEGORY = 'Repository'

# Where a plugin whose settings are reached the older way is listed.
LEGACY_PAGE = 'Other'

# One icon per category of the plugin vocabulary, plus the two pages that are
# not categories. Every name here is checked against the icon theme before it
# is used, so a missing one degrades rather than showing a broken glyph.
CATEGORY_ICONS = {
    REPOSITORY_PAGE: 'io.github.t00m.MiAZ-emblem-system-symbolic',
    LEGACY_PAGE:     'io.github.t00m.MiAZ-res-plugins',
    'Documents':     'io.github.t00m.MiAZ-res-concept',
    'Interface':     'io.github.t00m.MiAZ-config-symbolic',
    'Help':          'io.github.t00m.MiAZ-res-plugins',
}


class MiAZRepoSettingsPage(MiAZSidebarStack):
    """Every per-repository setting: the repository itself, then the plugins.

    One page per category rather than one long scroll. With every plugin
    enabled the old single page stacked ten groups, and the AI assistant's
    alone holds an expander per provider. The categories are not invented for
    this: the registry already hands its builders back sorted by the category
    each plugin declares.

    Plugin pages are built the first time this tab is shown, not when the
    dialog opens. Building AutoScan's group runs SANE and building the OCR one
    shells out to tesseract, and neither is worth paying for to look at the
    Metadata tab.
    """
    __gtype_name__ = 'MiAZRepoSettingsPage'

    def __init__(self, app):
        super().__init__(app)
        self.log = MiAZLog('MiAZ.RepoSettingsPage')
        self._built = False
        self._plugin_pages = []
        self._repository_page = None
        # The groups plugins put on the repository page. That page is never
        # thrown away, so nothing else takes them off before a rebuild.
        self._repository_plugin_groups = []
        self._sid_plugins_updated = None
        self._build_repository_page()
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
        """Whether the plugin pages have been built yet."""
        return self._built

    def build_plugin_groups(self):
        """Ask every enabled plugin for its settings, once.

        The registry returns builders sorted by category then plugin, so one
        pass fills each category page in order without sorting again here.
        """
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
                group.set_title(owner)
            self._page_for(category).add(group)
            if category == REPOSITORY_CATEGORY:
                self._repository_plugin_groups.append(group)
        self.build_legacy_rows()

    def build_legacy_rows(self):
        """One Configure row per plugin still using show_settings().

        No bundled plugin does. A plugin written against the older API, where
        the Plugins tab had a button that called show_settings(), keeps
        working: its dialog is reached from here instead, so the Settings tab
        is still the one place to look.
        """
        registry = self.app.get_service('plugin-system').settings
        offered = {owner for _category, owner, _builder in registry.builders()}
        plugin_system = self.app.get_service('plugin-system')
        group = None
        for plugin_info in plugin_system.plugins:
            if not plugin_system.is_plugin_loaded(plugin_info):
                continue
            name = plugin_info.get_name()
            if name in offered:
                continue
            plugin_obj = self.app.get_widget(f'plugin-{name}')
            if plugin_obj is None or not callable(getattr(plugin_obj, 'show_settings', None)):
                continue
            if group is None:
                group = Adw.PreferencesGroup(title=_('Other plugins'))
                self._page_for(LEGACY_PAGE).add(group)
            row = Adw.ActionRow(title=name)
            button = Gtk.Button(label=_('Configure'))
            button.set_valign(Gtk.Align.CENTER)
            button.connect('clicked',
                           lambda _b, obj=plugin_obj: obj.show_settings(self))
            row.add_suffix(button)
            group.add(row)

    def _page_for(self, category):
        """The Adw.PreferencesPage for one category, added on first use.

        Adding it only when something needs it is what keeps the list to the
        categories that actually have settings, rather than showing four
        headings of which two are empty.
        """
        if category == REPOSITORY_CATEGORY:
            # A setting about the repository belongs on the page about the
            # repository, not on a second page carrying the same name.
            return self._repository_page
        page = self.stack.get_child_by_name(category)
        if page is not None:
            return page
        page = Adw.PreferencesPage()
        title = _('Other plugins') if category == LEGACY_PAGE else _(category)
        self.add_page(category, title,
                      CATEGORY_ICONS.get(category, ''), page)
        self._plugin_pages.append(category)
        return page

    def _build_repository_page(self):
        repository = self.app.get_service('repo')
        config = self.app.get_config('Repository')
        repo_id = repository.get_active_id()

        page = Adw.PreferencesPage()
        self._repository_page = page
        self.add_page(REPOSITORY_PAGE, _('Repository'),
                      CATEGORY_ICONS[REPOSITORY_PAGE], page)

        # No heading: the page is already called Repository, and repeating it
        # over the first two rows reads as a narrower thing than it is. The
        # plugin groups below carry their own names.
        group = Adw.PreferencesGroup()
        page.add(group)

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
        """Throw the plugin pages away so the next showing rebuilds them.

        The repository page stays: it is not a plugin's and rebuilding it
        would lose whatever the user has half typed into the name row.
        """
        for category in self._plugin_pages:
            self.remove_page(category)
        self._plugin_pages = []
        # The repository page survives, so the groups plugins added to it have
        # to come off by hand. Without this the rebuild adds a second copy of
        # every Repository-category group.
        for group in self._repository_plugin_groups:
            self._repository_page.remove(group)
        self._repository_plugin_groups = []
        self._built = False
        if self.get_mapped():
            self.build_plugin_groups()
