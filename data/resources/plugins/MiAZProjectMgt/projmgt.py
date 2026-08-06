#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: projmgt.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for project management
"""

import os
from gettext import gettext as _

from gi.repository import Gio
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
        'Help':          'http://github.com/t00m/MiAZ/README.adoc',
        'Version':       '0.6',
        'Category':      'Content Organisation',
        'Subcategory':   'Tagging and Classification'
    }

# Virtual project bucket holding documents not belonging to any real project.
# It is never a real config key: it is shown as the first filter option in the
# sidebar (next to 'Any') and stored only in the assignment map (projects.json).
DEFAULT_PROJECT = 'None'

default_available_data = {}

# Model
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
        self.cnfprj = os.path.join(repo_dir_conf, 'projects.json')
        self.projects = {}
        self.revision = 0
        if not os.path.exists(self.cnfprj):
            self.save()
            self.log.debug("Created new config file for projects")
        self.projects = self.load()
        self.check()
        self.apply_defaults(DEFAULT_PROJECT)
        self.util.connect('filename-added', self._on_filename_added)
        self.util.connect('filename-renamed', self._on_filename_renamed)
        self.util.connect('filename-deleted', self._on_filename_deleted)

    def check(self):
        repository = self.app.get_service('repo')
        to_delete = []
        for project in self.projects:
            for doc in self.docs_in_project(project):
                docpath = os.path.join(repository.docs, doc)
                if not os.path.exists(docpath):
                    to_delete.append((doc, project))
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

    def _remove_nosave(self, project: str, doc: str) -> bool:
        found = False
        if len(project) == 0:
            for prj in self.projects:
                docs = self.projects[prj]
                if doc in docs:
                    found = True
                    docs.remove(doc)
                    self.projects[prj] = docs
                    self.log.debug(f"Removed '{doc}' from project '{prj}'")
        else:
            try:
                docs = self.projects[project]
                if doc in docs:
                    found = True
                    docs.remove(doc)
                    self.projects[project] = docs
                    self.log.debug(f"Removed '{doc}' from project '{project}'")
            except KeyError:
                self.log.warning(f"Project '{project}' doesn't exist")
        return found

    def remove(self, project: str, doc: str) -> None:
        found = self._remove_nosave(project, doc)
        if found:
            self.save()
            self.srvdlg.show_toast(_("Document removed from project"))
        else:
            self.log.debug(f"Document '{doc}' does not belong to project '{project}'")

    def remove_batch(self, project: str, docs: list, notify: bool = True) -> None:
        removed = 0
        for doc in docs:
            if self._remove_nosave(project, doc):
                removed += 1
        self.save()
        if notify and removed > 0:
            message = _("{count} documents removed from projects").format(count=removed)
            self.log.debug(message)
            self.srvdlg.show_toast(message)

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

    def __init__(self, app, config):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                         hexpand=True, vexpand=True)
        self.app = app
        self.config = config
        self.log = MiAZLog('MiAZ.ProjectTab')
        self.factory = self.app.get_service('factory')
        self.doc_id = None
        self.checks = {}

        self.set_margin_top(6)
        self.set_margin_bottom(6)
        self.set_margin_start(6)
        self.set_margin_end(6)

        label = Gtk.Label()
        label.set_xalign(0.0)
        label.add_css_class('dim-label')
        label.set_text(_('Projects this document belongs to'))
        self.append(label)

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
        self.empty.set_text(_('No projects available yet. Create one from Projects management.'))
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
        plugin_name = self.plugin.get_name()
        dropdown = self.app.get_widget(f'plugin-{plugin_name}-dropdown')
        if dropdown is not None:
            dd_parent = dropdown.get_parent()
            if dd_parent is not None:
                dd_parent.remove(dropdown)
            dd_size_group = self.app.get_widget('sidebar-dropdown-size-group')
            if dd_size_group is not None:
                dd_size_group.remove_widget(dropdown)
            plugin_dropdowns = self.app.get_widget('plugin-dropdowns')
            if plugin_dropdowns is not None and dropdown in plugin_dropdowns:
                plugin_dropdowns.remove(dropdown)
            self.app.remove_widget(f'plugin-{plugin_name}-dropdown')
        section = self.app.get_widget('sidebar-plugin-section')
        if section is not None and hasattr(self, '_sidebar_item'):
            section.remove(self._sidebar_item)
        self.workspace.unregister_filter_view(f'{i_title}')
        if hasattr(self, '_used_updated_handler'):
            self.config.disconnect(self._used_updated_handler)
        if hasattr(self, '_selected_item_handler') and dropdown is not None:
            dropdown.disconnect(self._selected_item_handler)
        if hasattr(self, '_startup_handler'):
            self.workspace.disconnect(self._startup_handler)
        self.plugin.unregister_document_tabs()
        self.app.set_service('Projects', None)
        self.plugin.set_started(False)

    def startup(self, *args):
        if not self.plugin.started():
            # Always reinstall workspace menu entries (cleared by _on_plugins_updated)
            submenu = self.plugin.install_menu_entry()
            plugin_menu = Gio.Menu()
            menuitem = self.factory.create_menuitem(
                f'{i_confname}-add',
                _('Assign document(s) to {i_confname}').format(i_confname=i_confname),
                self._set_property, None, ['<Control>p'])
            plugin_menu.append_item(menuitem)
            menuitem = self.factory.create_menuitem(
                f'{i_confname}-del',
                _('Unassign document(s) from any {i_confname}').format(i_confname=i_confname),
                self._unset_property, None, ['<Control><Shift>p'])
            plugin_menu.append_item(menuitem)
            menuitem = self.factory.create_menuitem(
                f'{i_confname}-mgt',
                _('Manage {i_confname}').format(i_confname=i_confname),
                self._manage_properties, None, ['<Control><Alt>p'])
            plugin_menu.append_item(menuitem)
            submenu.append_submenu(f"{i_title}", plugin_menu)

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
                    self.app.add_widget(f'plugin-{plugin_name}-dropdown', dropdown)
                    self.app.get_widget('plugin-dropdowns').append(dropdown)
                    self._used_updated_handler = self.config.connect('used-updated', self.actions.dropdown_populate, dropdown, item_type, True, True)
                    self.actions.dropdown_populate(self.config, dropdown, item_type, True, True)
                    self._selected_item_handler = dropdown.connect("notify::selected-item", self.workspace.update)
                    dropdown.set_size_request(190, -1)
                    dd_size_group = self.app.get_widget('sidebar-dropdown-size-group')
                    if dd_size_group is not None:
                        dd_size_group.add_widget(dropdown)
                    section = self.app.get_widget('sidebar-plugin-section')
                    if section is not None:
                        icon_path = self.plugin.get_icon_path()
                        if icon_path:
                            img = Gtk.Image.new_from_file(icon_path)
                            img.set_pixel_size(16)
                            img.set_valign(Gtk.Align.CENTER)
                            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                            box.set_hexpand(True)
                            box.append(img)
                            box.append(dropdown)
                            self._sidebar_item = box
                        else:
                            self._sidebar_item = dropdown
                        section.append(self._sidebar_item)
                    self.workspace.register_filter_view(f'{i_title}', self._do_filter_view)
            else:
                # Sidebar already set up
                self.srvprj = self.app.get_service('Projects')

            # Projects of the document being renamed, as a tab in that dialog.
            self.plugin.register_document_tab(
                name='projects',
                title=item_type.__title_plural__,
                factory=lambda app: MiAZProjectTab(app, self.config),
                weight=100)

            self.plugin.set_started(started=True)

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
        self._unset_property_real(selected_documents)
        # Documents must always belong to a project: fall back to the default
        if selected_documents:
            self.srvprj.add_batch(DEFAULT_PROJECT, selected_documents, notify=False)
            self.workspace.update()
            message = _("{count} documents unassigned").format(count=len(selected_documents))
            self.srvdlg.show_toast(message)

    def _unset_property_real(self, selected_documents):
        if not selected_documents:
            return False
        self.srvprj.remove_batch('', selected_documents, notify=False)
        self.workspace.update()
        return True

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
        configview = MiAZProjectsView(self.app, plugin=self.plugin, config=self.config)
        configview.update_views()
        dialog = self.srvdlg.show_noop(
            title=_('Manage {i_confname}').format(i_confname=i_confname),
            widget=configview, width=800, height=600)
        dialog.present(widget.get_root())
