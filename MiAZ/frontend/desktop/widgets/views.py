#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from abc import abstractmethod

import gi
gi.require_version('Adw', '1')
gi.require_version('Gtk', '4.0')
from gi.repository import Adw
from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import Pango

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnView
from MiAZ.frontend.desktop.widgets.columnview import ColIcon, ColLabel, ColMenuButton, ColCheck, ColButton
from MiAZ.backend.models import MiAZItem, Country, Group, Person, Purpose, File, Project


class MiAZColumnViewWorkspace(MiAZColumnView):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewWorkspace'

    def __init__(self, app):
        super().__init__(app, item_type=MiAZItem)
        self.log = get_logger('MiAZColumnViewWorkspace')
        self.backend = self.app.get_backend()
        self.factory_subtitle = Gtk.SignalListItemFactory()
        self.factory_subtitle.connect("setup", self._on_factory_setup_subtitle)
        self.factory_subtitle.connect("bind", self._on_factory_bind_subtitle)
        self.factory_active = Gtk.SignalListItemFactory()
        self.factory_active.connect("setup", self._on_factory_setup_active)
        self.factory_active.connect("bind", self._on_factory_bind_active)
        # ~ self.factory_icon = Gtk.SignalListItemFactory()
        # ~ self.factory_icon.connect("setup", self._on_factory_setup_icon)
        # ~ self.factory_icon.connect("bind", self._on_factory_bind_icon)
        self.factory_icon_type = Gtk.SignalListItemFactory()
        self.factory_icon_type.connect("setup", self._on_factory_setup_icon_type)
        self.factory_group = Gtk.SignalListItemFactory()
        self.factory_group.connect("setup", self._on_factory_setup_group)
        self.factory_group.connect("bind", self._on_factory_bind_group)
        self.factory_sentby = Gtk.SignalListItemFactory()
        self.factory_sentby.connect("setup", self._on_factory_setup_sentby)
        self.factory_sentby.connect("bind", self._on_factory_bind_sentby)
        self.factory_purpose = Gtk.SignalListItemFactory()
        self.factory_purpose.connect("setup", self._on_factory_setup_purpose)
        self.factory_purpose.connect("bind", self._on_factory_bind_purpose)
        self.factory_sentto = Gtk.SignalListItemFactory()
        self.factory_sentto.connect("setup", self._on_factory_setup_sentto)
        self.factory_sentto.connect("bind", self._on_factory_bind_sentto)
        self.factory_date = Gtk.SignalListItemFactory()
        self.factory_date.connect("setup", self._on_factory_setup_date)
        self.factory_date.connect("bind", self._on_factory_bind_date)
        self.factory_flag = Gtk.SignalListItemFactory()
        self.factory_flag.connect("setup", self._on_factory_setup_flag)
        self.factory_flag.connect("bind", self._on_factory_bind_flag)

        # Setup columnview columns
        self.column_subtitle = Gtk.ColumnViewColumn.new("Concept", self.factory_subtitle)
        self.column_active = Gtk.ColumnViewColumn.new("Active", self.factory_active)
        # ~ self.column_icon = Gtk.ColumnViewColumn.new("Icon", self.factory_icon)
        self.column_icon_type = Gtk.ColumnViewColumn.new("Type", self.factory_icon_type)
        self.column_group = Gtk.ColumnViewColumn.new("Group", self.factory_group)
        self.column_sentby = Gtk.ColumnViewColumn.new("Sent by", self.factory_sentby)
        self.column_sentto = Gtk.ColumnViewColumn.new("Sent to", self.factory_sentto)
        self.column_purpose = Gtk.ColumnViewColumn.new("Purpose", self.factory_purpose)
        self.column_date = Gtk.ColumnViewColumn.new("Date", self.factory_date)
        self.column_flag = Gtk.ColumnViewColumn.new("Country", self.factory_flag)

        # ~ self.cv.append_column(self.column_icon_type)
        self.cv.append_column(self.column_group)
        self.cv.append_column(self.column_purpose)
        self.cv.append_column(self.column_title)
        self.cv.append_column(self.column_subtitle)
        self.cv.append_column(self.column_sentby)
        self.cv.append_column(self.column_sentto)
        self.cv.append_column(self.column_date)
        self.cv.append_column(self.column_flag)
        self.column_title.set_expand(True)

        # Sorting
        self.prop_group_sorter = Gtk.CustomSorter.new(sort_func=self._on_sort_string_func, user_data='group')
        self.prop_purpose_sorter = Gtk.CustomSorter.new(sort_func=self._on_sort_string_func, user_data='purpose')
        self.prop_sentby_sorter = Gtk.CustomSorter.new(sort_func=self._on_sort_string_func, user_data='sentby_dsc')
        self.prop_concept_sorter = Gtk.CustomSorter.new(sort_func=self._on_sort_string_func, user_data='subtitle')
        self.prop_sentto_sorter = Gtk.CustomSorter.new(sort_func=self._on_sort_string_func, user_data='sentto_dsc')
        self.prop_date_sorter = Gtk.CustomSorter.new(sort_func=self._on_sort_string_func, user_data='date')
        self.prop_country_sorter = Gtk.CustomSorter.new(sort_func=self._on_sort_string_func, user_data='country')
        self.column_group.set_sorter(self.prop_group_sorter)
        self.column_purpose.set_sorter(self.prop_purpose_sorter)
        self.column_sentby.set_sorter(self.prop_sentby_sorter)
        self.column_subtitle.set_sorter(self.prop_concept_sorter)
        self.column_sentto.set_sorter(self.prop_sentto_sorter)
        self.column_date.set_sorter(self.prop_date_sorter)
        self.column_flag.set_sorter(self.prop_country_sorter)

        # Default sorting by date
        self.cv.sort_by_column(self.column_date, Gtk.SortType.DESCENDING)

    def _on_factory_setup_subtitle(self, factory, list_item):
        box = ColLabel()
        list_item.set_child(box)

    def _on_factory_bind_subtitle(self, factory, list_item):
        box = list_item.get_child()
        item = list_item.get_item()
        label = box.get_first_child()
        label.set_markup("<b>%s</b>" % item.subtitle)
        label.set_ellipsize(True)
        label.set_property('ellipsize', Pango.EllipsizeMode.MIDDLE)
        label.get_style_context().add_class(class_name='destructive-action')

    def _on_factory_setup_active(self, factory, list_item):
        box = ColCheck()
        list_item.set_child(box)
        button = box.get_first_child()

    def _on_factory_bind_active(self, factory, list_item):
        box = list_item.get_child()
        item = list_item.get_item()
        button = box.get_first_child()
        button.connect('toggled', self._on_button_toggled)
        button.set_active(item.active)

    def _on_factory_setup_icon(self, factory, list_item):
        box = ColIcon()
        list_item.set_child(box)

    def _on_factory_bind_icon(self, factory, list_item):
        """To be subclassed"""
        box = list_item.get_child()
        item = list_item.get_item()
        icon = box.get_first_child()

    def _on_factory_setup_icon_type(self, factory, list_item):
        box = ColButton()
        list_item.set_child(box)

    def _on_factory_bind_icon_type(self, factory, list_item):
        """To be subclassed"""
        box = list_item.get_child()
        button = box.get_first_child()
        self.log.debug(button)
        item = list_item.get_item()
        if item.valid:
            mimetype, val = Gio.content_type_guess('filename=%s' % item.id)
            gicon = Gio.content_type_get_icon(mimetype)
            icon_name = self.app.icman.choose_icon(gicon.get_names())
            self.log.debug(icon_name)
            child=Adw.ButtonContent(label='', icon_name=icon_name)
            button.set_child(child)
        else:
            child=Adw.ButtonContent(label='', icon_name='miaz-rename')
            button.set_child(child)

    def _on_factory_setup_group(self, factory, list_item):
        box = ColLabel()
        list_item.set_child(box)

    def _on_factory_bind_group(self, factory, list_item):
        box = list_item.get_child()
        item = list_item.get_item()
        label = box.get_first_child()
        group = item.group
        label.set_markup(group)

    def _on_factory_setup_date(self, factory, list_item):
        box = ColLabel()
        list_item.set_child(box)

    def _on_factory_bind_date(self, factory, list_item):
        box = list_item.get_child()
        item = list_item.get_item()
        label = box.get_first_child()
        date = item.date_dsc
        label.set_markup(date)

    def _on_factory_setup_sentby(self, factory, list_item):
        box = ColLabel()
        list_item.set_child(box)

    def _on_factory_bind_sentby(self, factory, list_item):
        box = list_item.get_child()
        item = list_item.get_item()
        label = box.get_first_child()
        label.set_markup(item.sentby_dsc)

    def _on_factory_setup_sentto(self, factory, list_item):
        box = ColLabel()
        list_item.set_child(box)

    def _on_factory_bind_sentto(self, factory, list_item):
        box = list_item.get_child()
        item = list_item.get_item()
        label = box.get_first_child()
        label.set_markup(item.sentto_dsc)

    def _on_factory_setup_purpose(self, factory, list_item):
        box = ColLabel()
        list_item.set_child(box)

    def _on_factory_bind_purpose(self, factory, list_item):
        box = list_item.get_child()
        item = list_item.get_item()
        label = box.get_first_child()
        purpose = item.purpose
        label.set_markup(purpose)

    def _on_factory_setup_flag(self, factory, list_item):
        box = ColIcon()
        list_item.set_child(box)

    def _on_factory_bind_flag(self, factory, list_item):
        box = list_item.get_child()
        item = list_item.get_item()
        icon = box.get_first_child()
        code = item.country
        flag = os.path.join(ENV['GPATH']['FLAGS'], "%s.svg" % code)
        if not os.path.exists(flag):
            flag = os.path.join(ENV['GPATH']['FLAGS'], "__.svg")
        icon.set_from_file(flag)
        icon.set_pixel_size(32)

    def _on_factory_setup_flag(self, factory, list_item):
        box = ColIcon()
        list_item.set_child(box)

class MiAZColumnViewCountry(MiAZColumnView):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewCountry'

    def __init__(self, app):
        super().__init__(app, item_type=Country)
        factory_flag = Gtk.SignalListItemFactory()
        factory_flag.connect("setup", self._on_factory_setup_flag)
        factory_flag.connect("bind", self._on_factory_bind_flag)
        self.column_flag = Gtk.ColumnViewColumn.new("Country", factory_flag)
        self.cv.append_column(self.column_flag)
        self.cv.append_column(self.column_id)
        self.cv.append_column(self.column_title)

    def _on_factory_setup_flag(self, factory, list_item):
        box = ColIcon()
        list_item.set_child(box)

    def _on_factory_bind_flag(self, factory, list_item):
        box = list_item.get_child()
        country = list_item.get_item()
        icon = box.get_first_child()
        flag = os.path.join(ENV['GPATH']['FLAGS'], "%s.svg" % country.id)
        if not os.path.exists(flag):
            flag = os.path.join(ENV['GPATH']['FLAGS'], "__.svg")
        icon.set_from_file(flag)
        icon.set_pixel_size(32)

class MiAZColumnViewGroup(MiAZColumnView):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewGroup'

    def __init__(self, app):
        super().__init__(app, item_type=Group)
        self.cv.append_column(self.column_id)
        self.column_title.set_title("Group Id")
        self.cv.append_column(self.column_title)
        self.column_title.set_title("Description")

class MiAZColumnViewProject(MiAZColumnView):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewProject'

    def __init__(self, app):
        super().__init__(app, item_type=Project)
        self.cv.append_column(self.column_id)
        self.column_title.set_title("Project Id")
        self.cv.append_column(self.column_title)
        self.column_title.set_title("Description")

class MiAZColumnViewPurpose(MiAZColumnView):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewPurpose'

    def __init__(self, app):
        super().__init__(app, item_type=Purpose)
        self.cv.append_column(self.column_id)
        self.column_title.set_title("Purpose Id")
        self.cv.append_column(self.column_title)
        self.column_title.set_title("Description")

class MiAZColumnViewPerson(MiAZColumnView):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewPerson'

    def __init__(self, app):
        super().__init__(app, item_type=Person)
        self.cv.append_column(self.column_id)
        self.column_id.set_title("Initials")
        self.cv.append_column(self.column_title)
        self.column_title.set_title("Full name")

class MiAZColumnViewMassRename(MiAZColumnView):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewMassRename'

    def __init__(self, app):
        super().__init__(app, item_type=File)
        self.cv.append_column(self.column_id)
        self.column_id.set_title("Source")
        self.column_id.set_expand(True)
        self.cv.append_column(self.column_title)
        self.column_title.set_title("Target")
        self.column_title.set_expand(True)

class MiAZColumnViewMassDelete(MiAZColumnView):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewMassDelete'

    def __init__(self, app):
        super().__init__(app, item_type=File)
        self.cv.append_column(self.column_id)
        self.column_id.set_title("Filename")
        self.column_id.set_expand(False)
        self.column_id.set_visible(False)
        self.cv.append_column(self.column_title)
        self.column_title.set_title("Document")
        self.column_title.set_expand(True)

class MiAZColumnViewMassProject(MiAZColumnView):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewMassProject'

    def __init__(self, app):
        super().__init__(app, item_type=File)
        self.cv.append_column(self.column_id)
        self.column_id.set_title("Filename")
        self.column_id.set_expand(False)
        self.column_id.set_visible(False)
        self.cv.append_column(self.column_title)
        self.column_title.set_title("Document")
        self.column_title.set_expand(True)