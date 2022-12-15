#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

import gi
from gi.repository import Adw
from gi.repository import Gdk
from gi.repository import Gtk

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.backend.models import File, Group, Subgroup, Person, Country, Purpose, Concept
from MiAZ.backend.config import MiAZConfigSettingsGroups
from MiAZ.backend.config import MiAZConfigSettingsSubgroups
from MiAZ.backend.config import MiAZConfigSettingsPerson
from MiAZ.backend.config import MiAZConfigSettingsCountries
from MiAZ.backend.config import MiAZConfigSettingsPurposes
from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnView, RowIcon
from MiAZ.frontend.desktop.widgets.dialogs import MiAZDialogAdd
from MiAZ.frontend.desktop.widgets.selector import MiAZSelector
from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnView
from MiAZ.frontend.desktop.widgets.columnviews import MiAZColumnViewCountry


class MiAZConfigView(MiAZSelector):
    """"""
    __gtype_name__ = 'MiAZConfigView'
    current = None
    config_local = None
    config_global = None
    config_for = None
    search_term = ''

    def __init__(self, app, config_for):
        super(MiAZSelector, self).__init__(spacing=12, orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        # ~ self.conf = self.app.get_conf()
        self.log = get_logger('MiAZConfigView')
        self.backend = self.app.get_backend()
        # ~ self.dir_repo = self.conf['App'].get('source')
        self.config_for = config_for
        self.factory = self.app.get_factory()
        self.set_vexpand(True)
        self.set_margin_top(margin=12)
        self.set_margin_end(margin=12)
        self.set_margin_start(margin=12)

    # ~ def _setup_view_finish(self):
        # ~ self.view.column_title.set_title(self.config_for.title())
        # ~ self.view.cv.append_column(self.view.column_title)
        # ~ self.view.column_title.set_expand(True)
        # ~ self.view.cv.sort_by_column(self.view.column_title, Gtk.SortType.ASCENDING)

    def _on_filter_selected(self, *args):
        self.viewAv.refilter()

    def _do_filter_view(self, item, filter_list_model):
        chunk = self.entry.get_text().upper()
        string = "%s%s" % (item.id, item.title)
        if chunk in string.upper():
            return True
        return False

    def on_key_released(self, widget, keyval, keycode, state):
        self.log.debug("Active window: %s", self.app.get_active_window())
        keyname = Gdk.keyval_name(keyval)
        self.log.debug("Key: %s", keyname)

    def _on_entrysearch_delete(self, *args):
        self.entry.set_text("")

    def _setup_view(self):
        selector = MiAZSelector(self.app)
        frmView = Gtk.Frame()
        self.view = MiAZColumnView(self.app)
        self.view.set_filter(self._do_filter_view)
        frmView.set_child(self.view)
        return selector

    def _on_item_add(self, *args):
        dialog = MiAZDialogAdd(self.app, self.get_root(), 'New %s' % self.config_for, '%s name' % self.config_for.title(), '')
        boxkey2 = dialog.get_boxKey2()
        boxkey2.set_visible(False)
        etyValue1 = dialog.get_value1_widget()
        search_term = self.entry.get_text()
        etyValue1.set_text(search_term)
        dialog.connect('response', self._on_response_item_add)
        dialog.show()

    def _on_response_item_add(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            value = dialog.get_value1()
            if len(value) > 0:
                items = self.config.load()
                if not value.upper() in items:
                    items.append(value.upper())
                    self.config.save(items)
                    self.log.debug("Added: %s", value.upper())
                    self.update()
        dialog.destroy()

    def _on_item_rename(self, *args):
        return

    def _on_item_remove(self, *args):
        item = self.view.get_item()
        if item is None:
            return
        self.config.remove(item.id)
        self.update()
        self.entry.set_text('')
        self.entry.activate()

    def config_set(self, config_for, config_local, config_global):
        self.config_for = config_for
        self.config_local = config_local
        self.config_global = config_global

    def update(self, items=None):
        return
        # FIXME: this is awful
        if items is None:
            items = []
            item_type = self.config.config_model
            database = self.config.load()
            if self.config.config_is is list:
                for key in database:
                    items.append(item_type(id=key, title=key))
            elif self.config.config_is is dict:
                if self.config.foreign:
                    gitems = self.config.load_global()
                    for key in database:
                        try:
                            items.append(item_type(id=key, title=gitems[key]))
                        except KeyError:
                            items.append(item_type(id=key, title=''))
                else:
                    for key in database:
                        items.append(item_type(id=key, title=database[key]))
        self.view.update(items)


class MiAZGroups(MiAZConfigView):
    """"""
    __gtype_name__ = 'MiAZGroups'
    current = None

    def __init__(self, app):
        backend = app.get_backend()
        dir_conf = backend.get_repo_conf_dir()
        self.config = MiAZConfigSettingsGroups(dir_conf)
        self.config_for = self.config.get_config_for()
        super(MiAZConfigView, self).__init__(app)
        super().__init__(app, self.config.config_for)
        self.log = get_logger('MiAZSettings-%s' % self.config_for)

class MiAZSubgroups(MiAZConfigView):
    """"""
    __gtype_name__ = 'MiAZSubgroups'
    current = None

    def __init__(self, app):
        backend = app.get_backend()
        dir_conf = backend.get_repo_conf_dir()
        self.config = MiAZConfigSettingsSubgroups(dir_conf)
        self.config_for = self.config.get_config_for()
        super(MiAZConfigView, self).__init__(app)
        super().__init__(app, self.config.config_for)
        self.log = get_logger('MiAZSettings-%s' % self.config_for)

class MiAZOrganizations(MiAZConfigView):
    """Class for managing Organizations from Settings"""
    __gtype_name__ = 'MiAZOrganizations'

    def __init__(self, app):
        backend = app.get_backend()
        dir_conf = backend.get_repo_conf_dir()
        self.config = MiAZConfigSettingsPerson(dir_conf)
        super(MiAZConfigView, self).__init__(app)
        super().__init__(app, self.config.config_for)

    def _on_item_add(self, *args):
        dialog = MiAZDialogAdd(self.app, self.get_root(), 'Add new %s' % self.config.config_for, 'Initials', 'Full name')
        etyValue1 = dialog.get_value1_widget()
        search_term = self.entry.get_text()
        etyValue1.set_text(search_term)
        dialog.connect('response', self._on_response_item_add)
        dialog.show()

    def _on_response_item_add(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            key = dialog.get_value1()
            value = dialog.get_value2()
            if len(key) > 0 and len(value) > 0:
                items = self.config.load()
                items[key.upper()] = value
                self.log.info("New organization: %s (%s)", key.upper(), value)
                self.config.save(items)
                self.update()
        dialog.destroy()

    def _setup_view_finish(self):
        self.view.column_id.set_title("Code")
        self.view.column_title.set_title(self.config_for.title())
        self.view.cv.append_column(self.view.column_id)
        self.view.cv.append_column(self.view.column_title)
        self.view.column_title.set_expand(True)
        self.view.cv.sort_by_column(self.view.column_title, Gtk.SortType.ASCENDING)


class MiAZCountries(MiAZConfigView):
    """"""
    __gtype_name__ = 'MiAZCountries'
    current = None

    def __init__(self, app):
        backend = app.get_backend()
        dir_conf = backend.get_repo_conf_dir()
        self.config = MiAZConfigSettingsCountries(dir_conf)

        super(MiAZConfigView, self).__init__(app, edit=False)
        super().__init__(app, self.config.config_for)
        dir_conf = self.backend.get_repo_conf_dir()
        self.icman = self.app.get_icman()

    def _on_item_remove(self, *args):
        return

    def _setup_view_finish(self):
        self.viewAv = MiAZColumnViewCountry(self.app)
        self.viewAv.set_filter(self._do_filter_view)
        self.viewAv.column_title.set_expand(True)
        self.scrWindowAv.set_child(self.viewAv)
        self.viewAv.cv.sort_by_column(self.viewAv.column_title, Gtk.SortType.ASCENDING)

    def update(self, items=None):
        if items is None:
            items = []
            item_type = self.config.config_model
            countries = self.config.load_global()
            # ~ print(countries)
            for code in countries:
                item = item_type(id=code, title=countries[code], icon='%s.svg' % code)
                # ~ print("%s > %s (%s)" % (item.id, item.title, item.icon))
                items.append(item)
        self.viewAv.update(items)


class MiAZPurposes(MiAZConfigView):
    """Class for managing Purposes from Settings"""
    __gtype_name__ = 'MiAZPurposes'

    def __init__(self, app):
        backend = app.get_backend()
        dir_conf = backend.get_repo_conf_dir()
        self.config = MiAZConfigSettingsPurposes(dir_conf)
        super(MiAZConfigView, self).__init__(app)
        super().__init__(app, self.config.config_for)

