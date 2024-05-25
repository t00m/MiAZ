#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: configview.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Custom selector views to manage configuration
"""

import os
from gettext import gettext as _

from gi.repository import Gtk

from MiAZ.backend.log import get_logger
from MiAZ.frontend.desktop.widgets.selector import MiAZSelector
from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnView
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewCountry
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewGroup
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewPurpose
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewPerson
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewProject
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewRepo
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewPlugin
from MiAZ.frontend.desktop.widgets.dialogs import MiAZDialogAddRepo
from MiAZ.backend.pluginsystem import MiAZPluginType


class MiAZConfigView(MiAZSelector):
    """"""
    __gtype_name__ = 'MiAZConfigView'
    config_for = None

    def __init__(self, app, config=None):
        super(MiAZSelector, self).__init__(spacing=0, orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.log = get_logger('MiAZConfigView')
        self.backend = self.app.get_service('backend')
        self.conf = self.backend.get_config()
        self.config = self.conf[config]
        self.config.connect('used-updated', self.update)
        self.config.connect('available-updated', self.update)
        self.set_vexpand(True)

    def update_config(self):
        self.config = self.conf[config]

    def get_config_for(self):
        return self.config.config_for

    def _setup_view(self):
        selector = MiAZSelector(self.app)
        frmView = Gtk.Frame()
        self.view = MiAZColumnView(self.app)
        self.view.set_filter(self._do_filter_view)
        frmView.set_child(self.view)
        return selector

    def _on_config_import(self, *args):
        self.log.debug("Import configuration for '%s'", self.config.config_for)

class MiAZRepositories(MiAZConfigView):
    """Manage Repositories"""
    __gtype_name__ = 'MiAZRepositories'
    current = None

    def __init__(self, app):
        self.app = app
        super(MiAZConfigView, self).__init__(app, edit=True)
        super().__init__(app, 'Repository')

    def _setup_view_finish(self):
        # Setup Available and Used Columns Views
        self.viewAv = MiAZColumnViewRepo(self.app)
        self.add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewRepo(self.app)
        self.add_columnview_used(self.viewSl)

    def on_item_available_add(self, *args):
        dialog = MiAZDialogAddRepo(self.app, self.app.win, 'Add a new repository', 'Repository name', 'Folder')
        dialog.connect('response', self._on_response_item_available_add)
        dialog.show()

    def _on_response_item_available_add(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            repo_name = dialog.get_value1()
            repo_path = dialog.get_value2()
            if len(repo_name) > 0 and os.path.exists(repo_path):
                self.config.add_available(repo_name, repo_path)
                self.log.debug("Repo '%s' added to list of available repositories", repo_name)
                self.update()
        dialog.destroy()

    def _on_item_available_rename(self, item):
        dialog = MiAZDialogAddRepo(self.app, self.app.win, _('Edit repository'), _('Repository name'), _('Folder'))
        repo_name = item.id
        dialog.set_value1(repo_name.replace('_', ' '))
        dialog.set_value2(item.title)
        dialog.connect('response', self._on_response_item_available_rename, item)
        dialog.show()


class MiAZCountries(MiAZConfigView):
    """Manage countries from Repo Settings. Edit disabled"""
    __gtype_name__ = 'MiAZCountries'
    current = None

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=False)
        super().__init__(app, 'Country')

    def _setup_view_finish(self):
        # Setup Available and Used Column Views
        self.viewAv = MiAZColumnViewCountry(self.app)
        self.add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewCountry(self.app)
        self.add_columnview_used(self.viewSl)

    def _update_view_available(self):
        items = []
        item_type = self.config.model
        countries = self.config.load_available()
        for code in countries:
            items.append(item_type(id=code, title=countries[code], icon='%s.svg' % code))
        self.viewAv.update(items)

    def _update_view_used(self):
        items = []
        item_type = self.config.model
        countries = self.config.load_used()
        for code in countries:
            items.append(item_type(id=code, title=countries[code], icon='%s.svg' % code))
        self.viewSl.update(items)


class MiAZGroups(MiAZConfigView):
    """Manage groups from Repo Settings"""
    __gtype_name__ = 'MiAZGroups'

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=True)
        super().__init__(app, 'Group')

    def _setup_view_finish(self):
        # Setup Available and Used Columns Views
        self.viewAv = MiAZColumnViewGroup(self.app)
        self.add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewGroup(self.app)
        self.add_columnview_used(self.viewSl)

class MiAZPeople(MiAZConfigView):
    """Class for managing People from Settings"""
    __gtype_name__ = 'MiAZPeople'

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=True)
        super().__init__(app, 'People')

    def _setup_view_finish(self):
        # Setup Available and Used Columns Views
        self.viewAv = MiAZColumnViewPerson(self.app)
        self.add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewPerson(self.app)
        self.add_columnview_used(self.viewSl)

class MiAZPeopleSentBy(MiAZConfigView):
    """Class for managing People from Settings"""
    __gtype_name__ = 'MiAZSentBy'

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=True)
        super().__init__(app, 'SentBy')
        # Trick to keep People sync for SentBy/SentTo
        self.config_paired = self.conf['SentTo']
        self.config_paired.connect('available-updated', self.update)

    def _setup_view_finish(self):
        # Setup Available and Used Columns Views
        self.viewAv = MiAZColumnViewPerson(self.app)
        self.add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewPerson(self.app)
        self.add_columnview_used(self.viewSl)

class MiAZPeopleSentTo(MiAZConfigView):
    """Class for managing People from Settings"""
    __gtype_name__ = 'MiAZSentTo'

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=True)
        super().__init__(app, 'SentTo')
        # Trick to keep People sync for SentBy/SentTo
        self.config_paired = self.conf['SentBy']
        self.config_paired.connect('available-updated', self.update)

    def _setup_view_finish(self):
        # Setup Available and Used Columns Views
        self.viewAv = MiAZColumnViewPerson(self.app)
        self.add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewPerson(self.app)
        self.add_columnview_used(self.viewSl)

class MiAZPurposes(MiAZConfigView):
    """Manage purposes from Repo Settings"""
    __gtype_name__ = 'MiAZPurposes'

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=True)
        super().__init__(app, 'Purpose')

    def _setup_view_finish(self):
        # Setup Available and Used Columns Views
        self.viewAv = MiAZColumnViewPurpose(self.app)
        self.add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewPurpose(self.app)
        self.add_columnview_used(self.viewSl)

class MiAZProjects(MiAZConfigView):
    """Manage projects from Repo Settings"""
    __gtype_name__ = 'MiAZProjects'

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=True)
        super().__init__(app, 'Project')

    def _setup_view_finish(self):
        # Setup Available and Used Columns Views
        self.viewAv = MiAZColumnViewProject(self.app)
        self.add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewProject(self.app)
        self.add_columnview_used(self.viewSl)

class MiAZDates(Gtk.Box):
    """"""
    __gtype_name__ = 'MiAZDates'

    def __init__(self, app):
        super(MiAZDates, self).__init__(orientation=Gtk.Orientation.VERTICAL)
        hbox = self.factory.create_box_horizontal()
        label = Gtk.Label()
        calendar = Gtk.Calendar()
        btnDate = self.factory.create_button_popover(icon_name='miaz-res-date', widgets=[calendar])
        hbox.append(btnDate)
        hbox.append(label)
        frame = Gtk.Frame()
        cv = MiAZColumnViewMassRename(self.app)
        cv.get_style_context().add_class(class_name='monospace')
        cv.set_hexpand(True)
        cv.set_vexpand(True)
        frame.set_child(cv)
        self.append(hbox)
        self.append(frame)
        sdate = datetime.strftime(datetime.now(), '%Y%m%d')
        iso8601 = "%sT00:00:00Z" % sdate
        calendar.connect('day-selected', calendar_day_selected, label, cv, self.selected_items)
        calendar.select_day(GLib.DateTime.new_from_iso8601(iso8601))
        calendar.emit('day-selected')
        dialog = self.factory.create_dialog_question(self.app.win, _('Mass renaming'), box, width=640, height=480)
        dialog.connect('response', self._on_mass_action_rename_date_response, calendar)
        dialog.show()

    def calendar_day_selected(calendar, label, columnview, items):
        adate = calendar.get_date()
        y = "%04d" % adate.get_year()
        m = "%02d" % adate.get_month()
        d = "%02d" % adate.get_day_of_month()
        sdate = "%s%s%s" % (y, m, d)
        ddate = datetime.strptime(sdate, '%Y%m%d')
        label.set_text(ddate.strftime('%A, %B %d %Y'))
        citems = []
        for item in items:
            source = os.path.basename(item.id)
            name, ext = self.util.filename_details(source)
            lname = name.split('-')
            lname[0] = sdate
            target = "%s.%s" % ('-'.join(lname), ext)
            citems.append(File(id=source, title=target))
        columnview.update(citems)


    def _on_mass_action_rename_date_response(self, dialog, response, calendar):
        if response == Gtk.ResponseType.ACCEPT:
            adate = calendar.get_date()
            y = "%04d" % adate.get_year()
            m = "%02d" % adate.get_month()
            d = "%02d" % adate.get_day_of_month()
            sdate = "%s%s%s" % (y, m, d)
            for item in self.selected_items:
                source = os.path.basename(item.id)
                name, ext = self.util.filename_details(source)
                lname = name.split('-')
                lname[0] = sdate
                target = "%s.%s" % ('-'.join(lname), ext)
                self.util.filename_rename(source, target)
        dialog.destroy()

class MiAZUserPlugins(MiAZConfigView):
    """Manage user plugins from Repo Settings. Edit disabled"""
    __gtype_name__ = 'MiAZUserPlugins'
    current = None

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=False)
        super().__init__(app, 'Plugin')
        self._update_view_available()

    def plugins_updated(self, *args):
        # ~ self._update_view_used()
        self._update_view_available()
        self.log.debug("Selector plugin views updated")

    def _setup_view_finish(self):
        # Setup Available and Used Column Views
        self.viewAv = MiAZColumnViewPlugin(self.app)
        self.add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewPlugin(self.app)
        self.add_columnview_used(self.viewSl)

    # ~ def _update_view_available(self):
        # ~ plugin_manager = self.app.get_service('plugin-manager')
        # ~ items = []
        # ~ item_type = self.config.model
        # ~ for plugin in plugin_manager.plugins:
            # ~ ptype = plugin_manager.get_plugin_type(plugin)
            # ~ if ptype == MiAZPluginType.USER:
                # ~ pid = plugin.get_module_name()
                # ~ title = plugin.get_description() #+ ' (v%s)' % plugin.get_version()
                # ~ items.append(item_type(id=pid, title=title))
        # ~ self.viewAv.update(items)

    def _on_item_used_remove(self, *args):
        plugin_manager = self.app.get_service('plugin-manager')
        plugins_used = self.config.load_used()
        for plugin_used in self.viewSl.get_selected_items():
            plugin = plugin_manager.get_plugin_info(plugin_used.id)
            if plugin.is_loaded():
                plugin_manager.unload_plugin(plugin)
                self.log.debug("Plugin %s unloaded", plugin.get_name())
            del(plugins_used[plugin_used.id])
        self.config.save_used(items=plugins_used)
        self._update_view_used()


    def _on_item_used_add(self, *args):
        plugin_manager = self.app.get_service('plugin-manager')
        changed = False
        plugins_used = self.config.load_used()
        for plugin_available in self.viewAv.get_selected_items():
            plugins_used[plugin_available.id] = plugin_available.title
            self.log.debug("Using %s (%s)", plugin_available.id, plugin_available.title)
            plugin = plugin_manager.get_plugin_info(plugin_available.id)
            if not plugin.is_loaded():
                plugin_manager.load_plugin(plugin)
                self.log.debug("Plugin %s loaded", plugin.get_name())
            changed = True
        if changed:
            self.config.save_used(items=plugins_used)
            self._update_view_used()

