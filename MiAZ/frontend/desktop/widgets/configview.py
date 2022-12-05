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


class MiAZConfigView(Gtk.Box):
    """"""
    __gtype_name__ = 'MiAZConfigView'
    current = None
    config_local = None
    config_global = None
    config_for = None
    search_term = ''

    def __init__(self, app, config_for):
        super(Gtk.Box, self).__init__(spacing=12, orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.log = get_logger('MiAZConfigView')
        self.backend = app.get_backend()
        self.config_for = config_for
        self.factory = self.app.get_factory()
        self.set_vexpand(True)
        self.set_margin_top(margin=12)
        self.set_margin_end(margin=12)
        self.set_margin_start(margin=12)

        # Entry and buttons for operations (edit/add/remove)
        self.box_oper = Gtk.Box(spacing=3, orientation=Gtk.Orientation.HORIZONTAL)
        self.box_oper.set_vexpand(False)
        box_entry = Gtk.Box(spacing=3, orientation=Gtk.Orientation.HORIZONTAL)
        box_entry.set_hexpand(True)
        self.entry = Gtk.Entry()
        self.entry.set_activates_default(True)
        self.entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, 'miaz-entry-clear')
        self.entry.set_icon_activatable(Gtk.EntryIconPosition.SECONDARY, True)
        self.entry.connect('icon-press', self._on_entrysearch_delete)
        self.entry.connect('changed', self._on_filter_selected)
        self.entry.set_hexpand(True)
        self.entry.set_has_frame(True)
        box_entry.append(self.entry)
        self.box_oper.append(box_entry)
        self.box_buttons = Gtk.Box(spacing=3, orientation=Gtk.Orientation.HORIZONTAL)
        self.box_buttons.set_hexpand(False)
        # ~ self.box_buttons.append(self.factory.create_button('miaz-edit', '', self._on_item_rename))
        # ~ self.box_buttons.append(Gtk.Separator.new(orientation=Gtk.Orientation.VERTICAL))
        self.box_buttons.append(self.factory.create_button('miaz-list-add', '', self._on_item_add, self.config_for))
        self.box_buttons.append(self.factory.create_button('miaz-list-remove', '', self._on_item_remove))
        self.box_oper.append(self.box_buttons)
        self.append(self.box_oper)
        widget = self._setup_view()
        self._setup_view_finish()
        self.append(widget)

    def _setup_view_finish(self):
        self.view.column_title.set_title(self.config_for.title())
        self.view.cv.append_column(self.view.column_title)
        self.view.column_title.set_expand(True)
        self.view.cv.sort_by_column(self.view.column_title, Gtk.SortType.ASCENDING)

    def _on_filter_selected(self, *args):
        self.view.refilter()

    def _do_filter_view(self, item, filter_list_model):
        chunk = self.entry.get_text().upper()
        string = "%s%s%s" % (item.id, item.title, item.subtitle)
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
        frmView = Gtk.Frame()
        self.view = MiAZColumnView(self.app)
        self.view.set_filter(self._do_filter_view)
        frmView.set_child(self.view)
        return frmView

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
        self.config = MiAZConfigSettingsGroups()
        self.config_for = self.config.get_config_for()
        super().__init__(app, self.config_for)
        self.log = get_logger('MiAZSettings-%s' % self.config_for)

class MiAZSubgroups(MiAZConfigView):
    """"""
    __gtype_name__ = 'MiAZSubgroups'
    current = None

    def __init__(self, app):
        self.config = MiAZConfigSettingsSubgroups()
        self.config_for = self.config.get_config_for()
        super().__init__(app, self.config_for)
        self.log = get_logger('MiAZSettings-%s' % self.config_for)

class MiAZOrganizations(MiAZConfigView):
    """Class for managing Organizations from Settings"""
    __gtype_name__ = 'MiAZOrganizations'

    def __init__(self, app):
        self.config = MiAZConfigSettingsPerson()
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
        self.config = MiAZConfigSettingsCountries()
        super().__init__(app, self.config.config_for)
        self.box_buttons.set_visible(False)
        self.icman = self.app.get_icman()

    def _on_item_remove(self, *args):
        return

    def _setup_view_finish(self):
        factory_icon = Gtk.SignalListItemFactory()
        factory_icon.connect("setup", self._on_factory_setup_icon)
        factory_icon.connect("bind", self._on_factory_bind_icon)
        self.view.column_id.set_title("Code")
        self.view.column_title.set_title(self.config_for.title())
        self.view.column_icon.set_title("Flag")
        self.view.column_icon.set_factory(factory_icon)
        self.view.column_active.set_title("Use")
        self.view.cv.append_column(self.view.column_icon)
        self.view.cv.append_column(self.view.column_id)
        self.view.cv.append_column(self.view.column_title)
        self.view.cv.append_column(self.view.column_active)
        self.view.column_title.set_expand(True)
        self.view.cv.sort_by_column(self.view.column_title, Gtk.SortType.ASCENDING)

    def _on_factory_setup_icon(self, factory, list_item):
        box = RowIcon()
        list_item.set_child(box)

    def _on_factory_bind_icon(self, factory, list_item):
        """To be subclassed"""
        box = list_item.get_child()
        item = list_item.get_item()
        icon = box.get_first_child()
        flag = os.path.join(ENV['GPATH']['FLAGS'], "%s.svg" % item.id)
        if not os.path.exists(flag):
            flag = os.path.join(ENV['GPATH']['FLAGS'], "__.svg")
        icon.set_from_file(flag)
        icon.set_pixel_size(32)

    def update(self, items=None):
        if items is None:
            items = []
            item_type = self.config.config_model
            database = self.config.load()
            countries = self.config.load_global()
            for code in countries:
                items.append(item_type(id=code, title=countries[code], active=False))
        self.view.update(items)


class MiAZPurposes(MiAZConfigView):
    """Class for managing Purposes from Settings"""
    __gtype_name__ = 'MiAZPurposes'

    def __init__(self, app):
        self.config = MiAZConfigSettingsPurposes()
        super().__init__(app, self.config.config_for)

