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
    config_for = None

    def __init__(self, app):
        super(MiAZSelector, self).__init__(spacing=0, orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.log = get_logger('MiAZConfigView')
        self.backend = self.app.get_backend()
        self.conf = self.backend.get_conf()
        self.dir_conf = self.backend.get_repo_conf_dir()
        self.factory = self.app.get_factory()
        self.set_vexpand(True)

    def get_config_for(self):
        return self.config.config_for

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
        dialog = MiAZDialogAdd(self.app, self.get_root(), 'New %s' % self.config.config_for, '%s name' % self.config.config_for.title(), '')
        etyValue1 = dialog.get_value1_widget()
        search_term = self.entry.get_text()
        etyValue1.set_text(search_term)
        dialog.connect('response', self._on_response_item_add)
        dialog.show()

    def _on_response_item_add(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            key = dialog.get_value1()
            value = dialog.get_value2()
            if len(key) > 0:
                items = self.config.load(self.config.available)
                if not key.upper() in items:
                    items[key.upper()] = value
                    self.log.debug("%s (%s) added to list of available items", key.upper(), value)
                    self.config.save(filepath=self.config.available, items=items)
                    self.update()
        dialog.destroy()

    def _on_item_rename(self, *args):
        return

    def _on_item_remove(self, *args):
        item = self.viewAv.get_item()
        self.log.debug("%s > %s > %s", item, item.id, item.title)
        if item is None:
            return
        self.config.remove(item.id)
        self.update()
        self.entry.set_text('')
        self.entry.activate()

    def update_available(self):
        items_available = []
        item_type = self.config.model
        items = self.config.load(self.config.available)
        for key in items:
            items_available.append(item_type(id=key, title=items[key]))
        self.viewAv.update(items_available)

    def update_used(self):
        items_used = []
        item_type = self.config.model
        items = self.config.load(self.config.used)
        for key in items:
            items_used.append(item_type(id=key, title=items[key]))
        self.viewSl.update(items_used)


class MiAZCountries(MiAZConfigView):
    """"""
    __gtype_name__ = 'MiAZCountries'
    current = None

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=False)
        super().__init__(app)
        self.config = self.conf['Country']

    def _setup_view_finish(self):
        # Setup Available Column View
        self.viewAv = MiAZColumnViewCountry(self.app)
        self.add_columnview_available(self.viewAv)

        # Setup Used Column View
        self.viewSl = MiAZColumnViewCountry(self.app)
        self.add_columnview_used(self.viewSl)

    def update_available(self):
        items = []
        item_type = self.config.model
        countries = self.config.load(self.config.available)
        for code in countries:
            items.append(item_type(id=code, title=countries[code], icon='%s.svg' % code))
        self.viewAv.update(items)

    def update_used(self):
        items = []
        item_type = self.config.model
        countries = self.config.load(self.config.used)
        for code in countries:
            items.append(item_type(id=code, title=countries[code], icon='%s.svg' % code))
        self.viewSl.update(items)

class MiAZGroups(MiAZConfigView):
    """"""
    __gtype_name__ = 'MiAZGroups'
    # ~ current = None

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=True)
        super().__init__(app)
        self.config = self.conf['Group']

    def _setup_view_finish(self):
        # Setup Available Column View
        self.viewAv = MiAZColumnViewGroup(self.app)
        self.add_columnview_available(self.viewAv)

        # Setup Used Column View
        self.viewSl = MiAZColumnViewGroup(self.app)
        self.add_columnview_used(self.viewSl)


class MiAZSubgroups(MiAZConfigView):
    """"""
    __gtype_name__ = 'MiAZSubgroups'


    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=True)
        super().__init__(app)
        self.config = self.conf['Subgroup']

    def _setup_view_finish(self):
        # Setup Available Column View
        self.viewAv = MiAZColumnViewSubgroup(self.app)
        self.add_columnview_available(self.viewAv)

        # Setup Used Column View
        self.viewSl = MiAZColumnViewSubgroup(self.app)
        self.add_columnview_used(self.viewSl)


class MiAZPeople(MiAZConfigView):
    """Class for managing People from Settings"""
    __gtype_name__ = 'MiAZPeople'

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=True)
        super().__init__(app)
        self.config = self.conf['Person']

    def _setup_view_finish(self):
        # Setup Available Column View
        self.viewAv = MiAZColumnViewPerson(self.app)
        self.add_columnview_available(self.viewAv)

        # Setup Used Column View
        self.viewSl = MiAZColumnViewPerson(self.app)
        self.add_columnview_used(self.viewSl)

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
                items = self.config.load(self.config.used)
                items[key.upper()] = value
                self.log.info("New person: %s (%s)", key.upper(), value)
                self.config.save(filepath=self.config.available, items=items)
                self.update()
        dialog.destroy()


class MiAZPurposes(MiAZConfigView):
    """Class for managing Purposes from Settings"""
    __gtype_name__ = 'MiAZPurposes'

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=True)
        super().__init__(app)
        self.config = self.conf['Purpose']

    def _setup_view_finish(self):
       # Setup Available Column View
        self.viewAv = MiAZColumnViewPurpose(self.app)
        self.add_columnview_available(self.viewAv)

        # Setup Used Column View
        self.viewSl = MiAZColumnViewPurpose(self.app)
        self.add_columnview_used(self.viewSl)


