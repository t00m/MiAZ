# pylint: disable=E1101

"""
# File: projmgt.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for project management
"""

import os
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Gtk

from MiAZ.backend.config import MiAZConfig
from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import File
from MiAZ.backend.models import MiAZModel
from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin
from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnViewSelector
from MiAZ.frontend.desktop.widgets.configview import MiAZConfigView
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewDocuments

plugin_info = {
        'Module':        'projmgt',
        'Name':          'MiAZProjectMgt',
        'Loader':        'Python3',
        'Description':   _('Project management'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2025 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'https://github.com/t00m/MiAZ/blob/main/README.md',
        'Version':       '0.6',
        'Category':      'Documents',
        'Subcategory':   'Projects',
        'MenuEntries':   [
            ('assign', _('Assign document(s) to projects'), ['<Control>p']),
            ('unassign', _('Unassign document(s) from any projects'), ['<Control><Shift>p']),
            ('manage', _('Manage projects'), ['<Control><Alt>p']),
        ]
    }

# Virtual project bucket holding documents not belonging to any real project.
# It is never a real config key: it is shown as the first filter option in the
# sidebar (next to 'Any') and stored only in the assignment map (projects.json).
DEFAULT_PROJECT = 'None'

default_available_data = {}

# Model
def is_total_wipe(to_delete: int, assigned: int, documents_in_repo: int) -> bool:
    """Would this consistency pass delete every assignment there is?

    check() removes the assignments of documents it cannot find. Finding none
    of them, while the repository is full of documents, does not mean the user
    deleted everything: it means this service and the repository on screen
    disagree about which repository is open. That is what emptied a real
    repository's projects on 14 August 2026.

    A repository that really is empty is a different thing, and clearing its
    assignments is correct.
    """
    if to_delete == 0 or assigned == 0:
        return False
    return to_delete >= assigned and documents_in_repo > 0


def writes_to_the_active_repository(own_conf: str, active_conf: str) -> bool:
    """Whether this service still belongs to the repository that is open.

    The service resolves the path to one repository's projects.json when it is
    built. Writing after the application moved to another repository puts one
    repository's assignments into another one's file.

    An active repository that cannot be resolved (shutdown, a failed load) is
    not a mismatch, and refusing there would drop a legitimate save.
    """
    if not active_conf:
        return True
    return os.path.normpath(own_conf) == os.path.normpath(active_conf)


class Project(MiAZModel):
    __gtype_name__ = 'Project'
    __title__ = _('Project')
    __title_plural__ = _('Projects')
    __config_name__ = 'projects'
    __config_name_available__ = 'projects'
    __config_name_used__ = 'projects'

item_type = Project
i_title = item_type.__title__
i_confname = item_type.__config_name__


class MiAZProject(GObject.GObject):
    """Service that manages document-to-project assignments.
    Merged from MiAZ.backend.projects into the plugin so the plugin
    owns its full data lifecycle."""
    __gtype_name__ = 'MiAZProject'

    def __init__(self, app):
        super().__init__()
        self.log = MiAZLog('MiAZ.Projects')
        self.app = app
        repository = self.app.get_service('repo')
        self.util = self.app.get_service('util')
        self.srvdlg = self.app.get_service('dialogs')
        repo_dir_conf = repository.get('dir_conf')
        # Kept so save() can tell whether the repository is still the one this
        # service was built for.
        self.conf_dir = repo_dir_conf
        self.cnfprj = os.path.join(repo_dir_conf, 'projects.json')
        self.projects = {}
        self.revision = 0
        if not os.path.exists(self.cnfprj):
            self.save()
            self.log.debug("Created new config file for projects")
        self.projects = self.load()
        self.check()
        self.apply_defaults(DEFAULT_PROJECT)
        # Kept so dispose() can give them back. This service outlives a single
        # activation only if nobody takes it away, and it must not: it holds
        # the path to one repository's projects.json.
        self._handlers = [
            self.util.connect('filename-added', self._on_filename_added),
            self.util.connect('filename-renamed', self._on_filename_renamed),
            self.util.connect('filename-deleted', self._on_filename_deleted),
        ]

    def dispose(self):
        """Stop listening. Called when the plugin that owns this is unloaded."""
        for handler_id in getattr(self, '_handlers', []):
            try:
                self.util.disconnect(handler_id)
            except (TypeError, ValueError):
                pass
        self._handlers = []

    def check(self):
        repository = self.app.get_service('repo')
        to_delete = []
        for project in self.projects:
            for doc in self.docs_in_project(project):
                docpath = os.path.join(repository.docs, doc)
                if not os.path.exists(docpath):
                    to_delete.append((doc, project))
        assigned = sum(len(docs) for docs in self.projects.values())
        try:
            documents_in_repo = len(self.util.get_files(repository.docs))
        except Exception:
            documents_in_repo = 0
        if is_total_wipe(len(to_delete), assigned, documents_in_repo):
            self.log.error(
                f"Refusing to drop all {assigned} project assignments: none of "
                f"them was found in '{repository.docs}', which holds "
                f"{documents_in_repo} documents. This service belongs to "
                f"'{self.cnfprj}'. Nothing was changed.")
            return

        for doc, project in to_delete:
            self._remove_nosave(project, doc)
        if to_delete:
            self.save()
            message = _("{count} documents removed from projects (no longer in the repository)").format(count=len(to_delete))
            self.log.warning(message)
            self.srvdlg.show_toast(message)
        self.log.debug("Projects consistency successfully checked")

    def _add_nosave(self, project: str, doc: str) -> bool:
        added = False
        try:
            docs = self.projects[project]
            if doc not in docs:
                docs.append(doc)
                self.projects[project] = docs
                added = True
        except KeyError:
            self.projects[project] = [doc]
            added = True
        if added:
            self.log.debug(f"Added '{doc}' to project '{project}'")
        return added

    def add(self, project: str, doc: str):
        if self._add_nosave(project, doc):
            self.save()
            self.srvdlg.show_toast(_("Document assigned to project '{project}'").format(project=project))

    def add_batch(self, project: str, docs: list, notify: bool = True) -> None:
        added = 0
        for doc in docs:
            if self._add_nosave(project, doc):
                added += 1
        self.save()
        if notify and added > 0:
            message = _("{count} documents assigned to project '{project}'").format(count=added, project=project)
            self.log.debug(message)
            self.srvdlg.show_toast(message)

    def apply_defaults(self, default_project: str) -> None:
        """Assign the default project to every repository document that does not
        belong to any project. Runs on activation, transparent to the user
        (no toasts), debug-logged only."""
        repository = self.app.get_service('repo')
        try:
            docs = self.util.get_files(repository.docs)
        except Exception:
            docs = []
        unassigned = [os.path.basename(fp) for fp in docs
                      if len(self.assigned_to(os.path.basename(fp))) == 0]
        for doc in unassigned:
            self._add_nosave(default_project, doc)
        if unassigned:
            self.save()
            self.log.debug(
                f"Default project '{default_project}' applied to "
                f"{len(unassigned)} document(s) without project")

    def _remove_nosave(self, project: str, doc: str) -> list:
        """Take a document out of one project, or out of all of them.

        Returns the names of the projects it was removed from. An empty list
        means it belonged to none, which is the old False. Callers use the
        names to say what happened: "unassigned" on its own left the user
        guessing which project they had just left.
        """
        removed = []
        if len(project) == 0:
            for prj in self.projects:
                docs = self.projects[prj]
                if doc in docs:
                    docs.remove(doc)
                    self.projects[prj] = docs
                    removed.append(prj)
                    self.log.debug(f"Removed '{doc}' from project '{prj}'")
        else:
            try:
                docs = self.projects[project]
                if doc in docs:
                    docs.remove(doc)
                    self.projects[project] = docs
                    removed.append(project)
                    self.log.debug(f"Removed '{doc}' from project '{project}'")
            except KeyError:
                self.log.warning(f"Project '{project}' doesn't exist")
        return removed

    def remove(self, project: str, doc: str) -> None:
        found = self._remove_nosave(project, doc)
        if found:
            self.save()
            self.srvdlg.show_toast(
                _("Document removed from project {projects}").format(
                    projects=', '.join(found)))
        else:
            self.log.debug(f"Document '{doc}' does not belong to project '{project}'")

    def remove_batch(self, project: str, docs: list, notify: bool = True) -> list:
        """Remove several documents and return the projects that lost one."""
        removed = 0
        projects = []
        for doc in docs:
            names = self._remove_nosave(project, doc)
            if names:
                removed += 1
                for name in names:
                    if name not in projects:
                        projects.append(name)
        self.save()
        if notify and removed > 0:
            message = _("{count} documents removed from {projects}").format(
                count=removed, projects=', '.join(projects))
            self.log.debug(message)
            self.srvdlg.show_toast(message)
        return projects

    def exists(self, project, doc):
        try:
            return doc in self.projects[project]
        except KeyError:
            return False

    def assigned_to(self, doc) -> list:
        return [prj for prj, docs in self.projects.items() if doc in docs]

    def docs_in_project(self, project):
        try:
            return self.projects[project]
        except KeyError:
            return []

    def list_all(self):
        for project, docs in self.projects.items():
            for doc in docs:
                self.log.debug(f"Project: {project} > Doc: {doc}")

    def save(self) -> None:
        # Refuse to write into a repository that is no longer the one open.
        # This service resolves its file once, when it is built, so a copy that
        # outlives a repository switch would otherwise put these assignments
        # into the repository the user left.
        repository = self.app.get_service('repo')
        active_conf = repository.conf if repository is not None else None
        if not writes_to_the_active_repository(self.conf_dir, active_conf):
            self.log.error(
                f"Refusing to write '{self.cnfprj}': the open repository is "
                f"'{active_conf}'. This service belongs to a repository that "
                f"is no longer the active one.")
            return
        util = self.app.get_service('util')
        util.json_save(self.cnfprj, self.projects)
        self.revision += 1

    def load(self) -> dict:
        self.revision += 1
        return self.util.json_load(self.cnfprj)

    def _on_filename_added(self, util, target):
        doc = os.path.basename(target)
        if len(self.assigned_to(doc)) == 0:
            self._add_nosave(DEFAULT_PROJECT, doc)
            self.save()
            self.log.debug(f"Default project '{DEFAULT_PROJECT}' assigned to new document '{doc}'")

    def _on_filename_renamed(self, util, source, target):
        source = os.path.basename(source)
        target = os.path.basename(target)
        projects = self.assigned_to(source)
        for project in projects:
            self._remove_nosave(project, source)
            self._add_nosave(project, target)
            self.log.debug(f"P[{project}]: {source} -> {target}")
        if projects:
            self.save()

    def _on_filename_deleted(self, util, target):
        docs = [os.path.basename(fp) for fp in target]
        self.remove_batch('', docs, notify=False)


# Configuration
class MiAZConfigProjects(MiAZConfig):
    def __init__(self, app, plugin):
        self.plugin = plugin
        config_dir = self.plugin.get_config_dir()
        config_file_setup = self.plugin.get_config_file_default_available_data()
        super().__init__(
            app=app,
            log=MiAZLog(f'MiAZ.Config.{i_title}'),
            config_for=f'{i_confname}',
            used=os.path.join(config_dir, f'{i_confname}-used.json'),
            available=os.path.join(config_dir, f'{i_confname}-available.json'),
            default=config_file_setup,
            model=item_type,
            must_copy=False
        )


# Columnview
class MiAZColumnViewProject(MiAZColumnViewSelector):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewProject'

    def __init__(self, app, available=True):
        item_type = Project
        super().__init__(app, item_type)
        self.cv.append_column(self.column_id)
        self.column_id.set_visible(False)
        self.column_title.set_title(_('Project Id'))
        self.cv.append_column(self.column_title)
        if available:
            title = _('{title} available').format(title=item_type.__title_plural__)
        else:
            title = _('{title} enabled').format(title=item_type.__title_plural__)
        self.column_title.set_title(title)


# Configuration view
class MiAZProjectsView(MiAZConfigView):
    """Manage projects from Repo Settings"""
    __gtype_name__ = 'MiAZProjectsView'

    def __init__(self, app, plugin, config):
        self.plugin = plugin
        self.config = config
        self.log = self.plugin.log
        self.config_dir = self.plugin.get_config_dir()
        self.data_dir = self.plugin.get_data_dir()
        self.data_file = self.plugin.get_data_file()
        if self.config_dir is None:
            raise RuntimeError("MiAZProjectsView: config_dir is None")
        super().__init__(app, config_name=f'{i_confname}', custom_config=config)

    def _setup_view_finish(self):
        self.viewAv = MiAZColumnViewProject(self.app)
        self._add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewProject(self.app, available=False)
        self._add_columnview_used(self.viewSl)
        self._add_config_menubutton(self.config.config_for)

    def _on_item_used_remove(self, *args):
        self.log.debug("_on_item_used_remove:: start")
        items_available = self.config.load_available()
        items_used = self.config.load_used()
        selected_item = self.viewSl.get_selected()
        item_type = self.config.model
        i_title = item_type.__title__
        item_id = selected_item.id.replace('_', ' ')
        item_desc = selected_item.title.replace('_', ' ')
        srvprj = self.app.get_service('Projects')
        srvdlg = self.app.get_service('dialogs')
        docs = srvprj.docs_in_project(selected_item.id)
        if len(docs) == 0:
            self.log.debug("_on_item_used_remove:: no dependencies")
            items_available[selected_item.id] = selected_item.title
            self.log.debug(f"{i_title} {item_id} added back to the list of available items")
            self.config.remove_used(selected_item.id)
            self.log.debug(f"{i_title} {item_id} removed from de list of used items")
            self.config.save_available(items=items_available)
            self.update_views()
            title = _('{i_title} management').format(i_title=i_title)
            body = _('{i_title} {item_desc} disabled').format(i_title=i_title, item_desc=item_desc)
            self.srvdlg.show_warning(title=title, body=body, parent=self)
        else:
            text = _('{i_title} {item_desc} is still being used by {count} documents').format(
                i_title=i_title, item_desc=item_desc, count=len(docs))
            self.log.error(text)
            window = self.viewSl.get_root()
            title = _('Action not possible')
            items = []
            for doc in docs:
                items.append(File(id=doc, title=os.path.basename(doc)))
            view = MiAZColumnViewDocuments(self.app)
            view.update(items)
            widget = Gtk.Frame()
            widget.set_child(view)
            srvdlg.show_error(title=title, body=text, widget=widget, width=600, height=480, parent=window)


# Rename dialog tab
class MiAZProjectTab(Gtk.Box):
    """Projects of a single document, shown as a tab in the rename dialog.

    Nothing is written while the user ticks boxes: the rename dialog calls
    apply() only after the document has actually been renamed, so cancelling
    leaves the assignments untouched.
    """
    __gtype_name__ = 'MiAZProjectTab'

    def __init__(self, app, config, show_manager=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                         hexpand=True, vexpand=True)
        self.app = app
        self.config = config
        self.log = MiAZLog('MiAZ.ProjectTab')
        self.factory = self.app.get_service('factory')
        # Opens the project manager. The tab only offers the button; the plugin
        # owns the dialog, which is also reachable from the workspace menu.
        self.show_manager = show_manager
        self.doc_id = None
        self.checks = {}

        self.set_margin_top(6)
        self.set_margin_bottom(6)
        self.set_margin_start(6)
        self.set_margin_end(6)

        header = self.factory.create_box_horizontal(spacing=6, hexpand=True)
        label = Gtk.Label()
        label.set_xalign(0.0)
        label.set_hexpand(True)
        label.add_css_class('dim-label')
        label.set_text(_('Projects this document belongs to'))
        header.append(label)
        if show_manager is not None:
            button = self.factory.create_button(
                icon_name='io.github.t00m.MiAZ-config-symbolic',
                title=_('Manage {i_confname}').format(i_confname=i_confname),
                tooltip=_('Create, rename or delete {i_confname}').format(i_confname=i_confname),
                callback=self._on_manage_clicked)
            button.set_valign(Gtk.Align.CENTER)
            header.append(button)
        self.append(header)

        self.listbox = Gtk.ListBox.new()
        self.listbox.set_hexpand(True)
        frame = Gtk.Frame()
        frame.set_child(self.listbox)
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_hexpand(True)
        scroll.set_child(frame)
        self.append(scroll)

        self.empty = Gtk.Label()
        self.empty.set_xalign(0.0)
        self.empty.add_css_class('dim-label')
        self.empty.set_text(_('No projects available yet. Create one with the Manage projects button.'))
        self.empty.set_visible(False)
        self.append(self.empty)

        self._build_rows()

    def _build_rows(self):
        projects = self.config.load_used()
        self.checks = {}
        for pid in sorted(projects, key=lambda key: projects[key].lower()):
            check = self.factory.create_button_check(title='', active=False)
            check.set_valign(Gtk.Align.CENTER)
            row = self.factory.create_actionrow(title=projects[pid], suffix=check)
            self.listbox.append(row)
            self.checks[pid] = check
        self.empty.set_visible(len(self.checks) == 0)

    def _on_manage_clicked(self, *args):
        """Open the project manager over the rename window."""
        dialog = self.show_manager(widget=self)
        if dialog is not None:
            dialog.connect('closed', self._on_manager_closed)

    def _on_manager_closed(self, *args):
        """Show the projects the manager left behind, ticks included.

        Nothing is written until the rename goes through, so what the user has
        ticked so far has to survive the rebuild. Projects created in the
        manager come in unticked.
        """
        ticked = {pid for pid, check in self.checks.items() if check.get_active()}
        row = self.listbox.get_first_child()
        while row is not None:
            following = row.get_next_sibling()
            self.listbox.remove(row)
            row = following
        self._build_rows()
        for pid, check in self.checks.items():
            check.set_active(pid in ticked)

    # Document tab contract
    def set_document(self, doc_id):
        self.doc_id = doc_id
        srvprj = self.app.get_service('Projects')
        assigned = set(srvprj.assigned_to(doc_id)) if srvprj is not None else set()
        for pid, check in self.checks.items():
            check.set_active(pid in assigned)

    def apply(self, old_id, new_id):
        """Write the ticked projects. True when something actually changed."""
        srvprj = self.app.get_service('Projects')
        if srvprj is None:
            return False
        wanted = {pid for pid, check in self.checks.items() if check.get_active()}
        if wanted == set(srvprj.assigned_to(new_id)):
            return False
        # Same order as the workspace action: clear every assignment, then add
        # the chosen ones. A document always belongs somewhere, so an empty
        # selection falls back to the default bucket.
        srvprj.remove_batch('', [new_id], notify=False)
        for pid in wanted:
            srvprj.add_batch(pid, [new_id], notify=False)
        if not wanted:
            srvprj.add_batch(DEFAULT_PROJECT, [new_id], notify=False)
        workspace = self.app.get_widget('workspace')
        if workspace is not None:
            workspace.update()
        return True


class MiAZProjectMgt(MiAZExtension):
    __gtype_name__ = 'MiAZProjectMgt'
    plugin = None

    def do_activate(self):
        """Plugin activation"""
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)
        self._filter_cache_key = None
        self._filter_cache_set = set()
        self.plugin.register(self, plugin_info)
        self.log = self.plugin.get_logger()
        self.actions = self.app.get_service('actions')
        self.factory = self.app.get_service('factory')
        self.srvdlg = self.app.get_service('dialogs')
        self.util = self.app.get_service('util')
        self.workspace = self.app.get_widget('workspace')
        if self.workspace.is_loaded():
            self.startup()
        else:
            self._startup_handler = self.workspace.connect('workspace-loaded', self.startup)

    def do_deactivate(self):
        # The sidebar dropdown and everything it was wired into are taken back
        # by the plugin system, which owns what add_sidebar_dropdown handed it.
        plugin_name = self.plugin.get_name()
        dropdown = self.app.get_widget(f'plugin-{plugin_name}-dropdown')
        self.workspace.unregister_filter_view(f'{i_title}')
        self.workspace.unregister_query_hook(f'{i_title}')
        if hasattr(self, '_used_updated_handler'):
            self.config.disconnect(self._used_updated_handler)
        if hasattr(self, '_selected_item_handler') and dropdown is not None:
            dropdown.disconnect(self._selected_item_handler)
        if hasattr(self, '_startup_handler'):
            self.workspace.disconnect(self._startup_handler)
        self.plugin.unregister_document_tabs()
        # Take the service down rather than leaving it registered: it listens
        # to the file signals and writes the projects file of the repository
        # it was built for. Kept across a repository switch it wrote project
        # assignments into the repository that was left.
        srvprj = self.app.get_service('Projects')
        if srvprj is not None:
            srvprj.dispose()
        self.app.set_service('Projects', None)
        self.plugin.set_started(False)

    def startup(self, *args):
        if not self.plugin.started():
            # Always reinstall workspace menu entries (cleared by
            # _on_plugins_updated). The three actions go straight into the
            # plugin's own menu entry. They used to hang off a submenu named
            # after the plugin, inside the entry already named after the
            # plugin, so reaching Assign meant Projects then Project then
            # Assign.
            self.plugin.install_menu_entries({
                'assign': self._set_property,
                'unassign': self._unset_property,
                'manage': self._manage_properties,
            })

            # One-time setup guarded by the dropdown widget sentinel.
            # When _on_plugins_updated calls startup() a second time the dropdown
            # already exists, so we skip re-creating config/service/sidebar widgets
            # and only re-sync self.srvprj to the already-registered service.
            plugin_name = self.plugin.get_name()
            if self.app.get_widget(f'plugin-{plugin_name}-dropdown') is None:
                # Write factory data for config
                filepath = self.plugin.get_config_file_default_available_data()
                self.util.json_save(filepath, default_available_data)

                # Initialise configuration
                self.config = MiAZConfigProjects(self.app, self.plugin)

                # 'None' is a virtual filter option (injected first in the
                # dropdown via none_value=True), never a real config key. Drop
                # it from the registries if an earlier version persisted it.
                self._purge_default_value()

                # Initialise project service and register it for other components to use
                existing = self.app.get_service('Projects')
                if existing is None:
                    self.srvprj = MiAZProject(self.app)
                    self.app.set_service('Projects', self.srvprj)
                else:
                    self.srvprj = existing

                # Dropdown for custom filters
                dropdown = self.app.get_widget(f'plugin-{plugin_name}-dropdown')
                if dropdown is None:
                    dropdown = self.factory.create_dropdown_generic(item_type=item_type, ellipsize=True, enable_search=True)
                    self._used_updated_handler = self.config.connect('used-updated', self.actions.dropdown_repopulate, dropdown, item_type, True, True)
                    self.actions.dropdown_populate(self.config, dropdown, item_type, True, True)
                    self._selected_item_handler = dropdown.connect("notify::selected-item", self.workspace.update)
                    # Sizing, the shared size group, the plugin-dropdowns list,
                    # the widget key and the icon row, teardown included.
                    self.plugin.add_sidebar_dropdown(dropdown)
                    self.workspace.register_filter_view(f'{i_title}', self._do_filter_view)
                    self.workspace.register_query_hook(f'{i_title}', self._adjust_query)
            else:
                # Sidebar already set up
                self.srvprj = self.app.get_service('Projects')

            # Projects of the document being renamed, as a tab in that dialog.
            self.plugin.register_document_tab(
                name='projects',
                title=item_type.__title_plural__,
                factory=lambda app: MiAZProjectTab(app, self.config, self.show_settings),
                weight=100)

            self.plugin.set_started(started=True)

    def _project_selected(self):
        """The selected project id, or None when the dropdown says 'Any'."""
        plugin_name = self.plugin.get_name()
        dropdown = self.app.get_widget(f'plugin-{plugin_name}-dropdown')
        if dropdown is None:
            return None
        selected_item = dropdown.get_selected_item()
        if selected_item is None or selected_item.id == 'Any':
            return None
        return selected_item.id

    def _adjust_query(self, query):
        """Lift the date and active checks while a project is selected.

        Project members may carry field values the repository config does not
        recognise, or any date at all, and the user still wants to see the whole
        project. The workspace used to hardcode this bypass by looking up this
        plugin's dropdown by name.
        """
        if self._project_selected() is not None:
            query.ignore_date = True
            query.ignore_active = True

    def _do_filter_view(self, item, filter_list_model):
        plugin_name = self.plugin.get_name()
        dropdown = self.app.get_widget(f'plugin-{plugin_name}-dropdown')
        selected_item = dropdown.get_selected_item()
        if selected_item is None:
            return True

        pid = selected_item.id
        if pid == 'Any':
            return True
        # Build the membership set once per filter pass instead of once per
        # document. The (pid, revision) key rebuilds it only when the selection
        # or the project assignments change. ('None' is a virtual filter option,
        # but unassigned docs live in the 'None' bucket, so this path covers it.)
        cache_key = (pid, self.srvprj.revision)
        if self._filter_cache_key != cache_key:
            self._filter_cache_key = cache_key
            self._filter_cache_set = set(self.srvprj.docs_in_project(pid))
        return item.id in self._filter_cache_set

    def _set_property(self, *args):
        selected_items = self.workspace.get_selected_items()
        if len(selected_items) > 0:
            dropdown = self.factory.create_dropdown_generic(item_type=item_type, ellipsize=True, enable_search=True)
            self.actions.dropdown_populate(self.config, dropdown, item_type, False, False)
            dialog = self.srvdlg.show_action(
                title=_('Manage {i_confname}').format(i_confname=i_confname),
                widget=dropdown)
            dialog.connect('response', self._on_set_property_response, dropdown)
            dialog.present(self.workspace.get_root())
        else:
            parent = self.app.get_widget('window')
            title = _('Project management')
            body1 = _('Action ignored')
            body2 = _('You must select at least one document')
            body = body1 + '\n' + body2
            self.srvdlg.show_error(title=title, body=body, parent=parent)

    def _on_set_property_response(self, dialog, response, dropdown):
        if response == 'apply':
            selected_documents = [item.id for item in self.workspace.get_selected_items()]
            config_item = dropdown.get_selected_item()
            self._unset_property_real(selected_documents)
            change = self._set_property_real(selected_documents, config_item.id)
            if change:
                self.workspace.update()

    def _set_property_real(self, selected_documents, pid):
        if not selected_documents:
            return False
        self.srvprj.add_batch(pid, selected_documents)
        return True

    def _purge_default_value(self):
        """The 'None' bucket must never be a real config key: it is rendered as
        the first filter option (next to 'Any') via none_value=True. Remove it
        from the available/used registries if an earlier version stored it."""
        if self.config.exists_used(DEFAULT_PROJECT):
            self.config.remove_used(DEFAULT_PROJECT)
        if self.config.exists_available(DEFAULT_PROJECT):
            self.config.remove_available(DEFAULT_PROJECT)

    def _unset_property(self, *args):
        # FIXME: somehow the user should decide from which projects
        selected_documents = [item.id for item in self.workspace.get_selected_items()]
        projects = self._unset_property_real(selected_documents)
        # Documents must always belong to a project: fall back to the default
        if selected_documents:
            self.srvprj.add_batch(DEFAULT_PROJECT, selected_documents, notify=False)
            self.workspace.update()
            # Name the projects. The shortcut removes the documents from every
            # project they were in, and a toast reading "3 documents
            # unassigned" left the user with no idea which ones those were.
            if projects:
                message = _("{count} documents removed from {projects}").format(
                    count=len(selected_documents), projects=', '.join(projects))
            else:
                message = _("{count} documents belonged to no project").format(
                    count=len(selected_documents))
            self.srvdlg.show_toast(message)

    def _unset_property_real(self, selected_documents):
        """Remove the selection from every project. Returns the ones touched."""
        if not selected_documents:
            return []
        projects = self.srvprj.remove_batch('', selected_documents, notify=False)
        self.workspace.update()
        return projects

    def project_view(self, *args):
        def _on_selected_project(dropdown, gparamobject, cv):
            srvprj = self.app.get_service('Projects')
            pid = dropdown.get_selected_item().id
            docs = srvprj.docs_in_project(pid)
            items = [File(id=doc, title=doc) for doc in docs]
            cv.update(items)
            message = _("{count} documents in project {pid}").format(count=len(docs), pid=pid)
            self.log.debug(message)
            self.srvdlg.show_toast(message)

        frame = Gtk.Frame()
        cv = MiAZColumnViewDocuments(self.app)
        frame.set_child(cv)
        cv.set_hexpand(True)
        cv.set_vexpand(True)

        dropdown = self.factory.create_dropdown_generic(Project)
        dropdown.connect('notify::selected-item', _on_selected_project, cv)
        self.actions.dropdown_populate(self.config, dropdown, Project, any_value=False)

        box = self.factory.create_box_vertical(hexpand=True, vexpand=True)
        box.add_css_class('toolbar')
        box.append(dropdown)
        box.append(frame)
        window = self.app.get_widget('window')
        dialog = self.srvdlg.show_noop(title=_('Documents per project'), widget=box, width=800, height=600)
        dialog.present(window)

    def _manage_properties(self, *args):
        parent = self.app.get_widget('window')
        self.show_settings(widget=parent)

    def show_settings(self, widget: Gtk.Widget = None):
        """Open the project manager over the window holding `widget`.

        The dialog is returned so a caller that has to react to what the user
        did there (the rename dialog tab rebuilds its list) can connect to it.
        """
        configview = MiAZProjectsView(self.app, plugin=self.plugin, config=self.config)
        configview.update_views()
        dialog = self.srvdlg.show_noop(
            title=_('Manage {i_confname}').format(i_confname=i_confname),
            widget=configview, width=800, height=600)
        dialog.present(widget.get_root())
        return dialog
