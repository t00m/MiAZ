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
from MiAZ.backend.config import MiAZConfigSettingsPeople
from MiAZ.backend.config import MiAZConfigSettingsCountries
from MiAZ.backend.config import MiAZConfigSettingsPurposes
from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnView, ColIcon
from MiAZ.frontend.desktop.widgets.dialogs import MiAZDialogAdd
from MiAZ.frontend.desktop.widgets.selector import MiAZSelector
from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnView
from MiAZ.frontend.desktop.widgets.columnviews import MiAZColumnViewCountry
from MiAZ.frontend.desktop.widgets.columnviews import MiAZColumnViewGroup
from MiAZ.frontend.desktop.widgets.columnviews import MiAZColumnViewSubgroup
from MiAZ.frontend.desktop.widgets.columnviews import MiAZColumnViewPurpose
from MiAZ.frontend.desktop.widgets.columnviews import MiAZColumnViewPerson


class MiAZConfigView(MiAZSelector):
    """"""
    __gtype_name__ = 'MiAZConfigView'
    current = None
    config_local = None
    config_global = None
    config_for = None
    search_term = ''

    def __init__(self, app, config_for):
        super(MiAZSelector, self).__init__(spacing=3, orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        # ~ self.conf = self.app.get_conf()
        self.log = get_logger('MiAZConfigView')
        self.backend = self.app.get_backend()
        self.dir_conf = self.backend.get_repo_conf_dir()
        self.config_for = config_for
        self.factory = self.app.get_factory()
        self.set_vexpand(True)
        self.set_margin_top(margin=6)
        self.set_margin_end(margin=6)
        self.set_margin_start(margin=6)

    def _on_filter_selected(self, *args):
        self.viewAv.refilter()
        self.viewSl.refilter()

    def _do_filter_view(self, item, filter_list_model):
        chunk = self.entry.get_text().upper()
        string = "%s%s" % (item.id, item.title)
        if chunk in string.upper():
            return True
        return False

    def on_key_released(self, widget, keyval, keycode, state):
        # ~ self.log.debug("Active window: %s", self.app.get_active_window())
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
                items = self.config.load(self.config.config_available)
                if not value.upper() in items:
                    items.append(value.upper())
                    self.config.save(items=items)
                    self.update()
        dialog.destroy()

    def _on_item_rename(self, *args):
        return

    def _on_item_remove(self, *args):
        item = self.viewAv.get_item()
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


class MiAZCountries(MiAZConfigView):
    """"""
    __gtype_name__ = 'MiAZCountries'
    current = None

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=False)
        self.config = MiAZConfigSettingsCountries(self.dir_conf)
        super().__init__(app, self.config.config_for)
        self.set_config_file_available(self.config.config_global)
        self.set_config_file_selected(self.config.config_local)

    def _setup_view_finish(self):
        # Setup Available Column View
        self.viewAv = MiAZColumnViewCountry(self.app)
        self.add_columnview_available(self.viewAv)

        # Setup Selected Column View
        self.viewSl = MiAZColumnViewCountry(self.app)
        self.add_columnview_selected(self.viewSl)

    def update_available(self):
        items = []
        item_type = self.config.config_model
        countries = self.config.load(self.conf_available)
        for code in countries:
            items.append(item_type(id=code, title=countries[code], icon='%s.svg' % code))
        self.viewAv.update(items)

    def update_selected(self):
        items = []
        item_type = self.config.config_model
        countries = self.config.load(self.dir_conf_selected)
        for code in countries:
            items.append(item_type(id=code, title=countries[code], icon='%s.svg' % code))
        self.viewSl.update(items)

class MiAZGroups(MiAZConfigView):
    """"""
    __gtype_name__ = 'MiAZGroups'
    current = None

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=True)
        self.config = MiAZConfigSettingsGroups(self.dir_conf)
        super().__init__(app, self.config.config_for)
        self.set_config_file_available(self.config.config_available)
        self.set_config_file_selected(self.config.config_local)

    def _setup_view_finish(self):
        # Setup Available Column View
        self.viewAv = MiAZColumnViewGroup(self.app)
        self.add_columnview_available(self.viewAv)

        # Setup Selected Column View
        self.viewSl = MiAZColumnViewGroup(self.app)
        self.add_columnview_selected(self.viewSl)

    def update_available(self):
        items = []
        item_type = self.config.config_model
        groups = self.config.load(self.conf_available)
        for group in groups:
            items.append(item_type(id=group, title=group))
        self.viewAv.update(items)

    def update_selected(self):
        items = []
        item_type = self.config.config_model
        groups = self.config.load(self.dir_conf_selected)
        for group in groups:
            items.append(item_type(id=group, title=group))
        self.viewSl.update(items)

class MiAZSubgroups(MiAZConfigView):
    """"""
    __gtype_name__ = 'MiAZSubgroups'
    current = None

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=False)
        self.config = MiAZConfigSettingsSubgroups(self.dir_conf)
        super().__init__(app, self.config.config_for)
        self.set_config_file_available(self.config.config_global)
        self.set_config_file_selected(self.config.config_local)

    def _setup_view_finish(self):
        # Setup Available Column View
        self.viewAv = MiAZColumnViewSubgroup(self.app)
        self.add_columnview_available(self.viewAv)

        # Setup Selected Column View
        self.viewSl = MiAZColumnViewSubgroup(self.app)
        self.add_columnview_selected(self.viewSl)

    def update_available(self):
        items = []
        item_type = self.config.config_model
        subgroups = self.config.load(self.conf_available)
        for subgroup in subgroups:
            items.append(item_type(id=subgroup, title=subgroup))
        self.viewAv.update(items)

    def update_selected(self):
        items = []
        item_type = self.config.config_model
        subgroups = self.config.load(self.dir_conf_selected)
        for subgroup in subgroups:
            items.append(item_type(id=subgroup, title=subgroup))
        self.viewSl.update(items)

class MiAZPeople(MiAZConfigView):
    """Class for managing People from Settings"""
    __gtype_name__ = 'MiAZPeople'

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=False)
        self.config = MiAZConfigSettingsPeople(self.dir_conf)
        super().__init__(app, self.config.config_for)
        self.set_config_file_available(self.config.config_global)
        self.set_config_file_selected(self.config.config_local)

    def _setup_view_finish(self):
        # Setup Available Column View
        self.viewAv = MiAZColumnViewPerson(self.app)
        self.add_columnview_available(self.viewAv)

        # Setup Selected Column View
        self.viewSl = MiAZColumnViewPerson(self.app)
        self.add_columnview_selected(self.viewSl)

    def update_available(self):
        items = []
        item_type = self.config.config_model
        people = self.config.load(self.conf_available)
        for pid in people:
            items.append(item_type(id=pid, title=people[pid]))
        self.viewAv.update(items)

    def update_selected(self):
        items = []
        item_type = self.config.config_model
        people = self.config.load(self.dir_conf_selected)
        for pid in people:
            items.append(item_type(id=pid, title=people[pid]))
        self.viewSl.update(items)

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
                items = self.config.load(self.config.config_local)
                items[key.upper()] = value
                self.log.info("New person: %s (%s)", key.upper(), value)
                self.config.save(items=items)
                self.update()
        dialog.destroy()


class MiAZPurposes(MiAZConfigView):
    """Class for managing Purposes from Settings"""
    __gtype_name__ = 'MiAZPurposes'

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=False)
        self.config = MiAZConfigSettingsPurposes(self.dir_conf)
        super().__init__(app, self.config.config_for)
        self.set_config_file_available(self.config.config_global)
        self.set_config_file_selected(self.config.config_local)

    def _setup_view_finish(self):
       # Setup Available Column View
        self.viewAv = MiAZColumnViewPurpose(self.app)
        self.add_columnview_available(self.viewAv)

        # Setup Selected Column View
        self.viewSl = MiAZColumnViewPurpose(self.app)
        self.add_columnview_selected(self.viewSl)

    def update_available(self):
        items = []
        item_type = self.config.config_model
        purposes = self.config.load(self.conf_available)
        for purpose in purposes:
            items.append(item_type(id=purpose, title=purpose))
        self.viewAv.update(items)

    def update_selected(self):
        items = []
        item_type = self.config.config_model
        purposes = self.config.load(self.dir_conf_selected)
        for purpose in purposes:
            items.append(item_type(id=purpose, title=purpose))
        self.viewSl.update(items)
