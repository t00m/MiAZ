#!/usr/bin/python3
# File: views.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Different views based on ColumnView widget

import os
from gettext import gettext as _

from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import Pango

from MiAZ.backend.log import MiAZLog
from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnView
from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnViewSelector
from MiAZ.frontend.desktop.widgets.columnview import ColIcon, ColLabel, ColCheck
from MiAZ.backend.models import MiAZItem, Country, Group, Person, Purpose, File, Project, Repository, Plugin, Concept


class MiAZColumnViewWorkspace(MiAZColumnView):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewWorkspace'

    def __init__(self, app):
        super().__init__(app, item_type=MiAZItem)
        self.log = MiAZLog('MiAZColumnViewWorkspace')
        self.srvicm = self.app.get_service('icons')
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
        self.factory_icon_type.connect("bind", self._on_factory_bind_icon_type)
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
        # ~ self.factory_country = Gtk.SignalListItemFactory()
        # ~ self.factory_country.connect("setup", self._on_factory_setup_country)
        # ~ self.factory_country.connect("bind", self._on_factory_bind_country)

        # Setup columnview columns
        self.column_subtitle = Gtk.ColumnViewColumn.new(_('Concept'), self.factory_subtitle)
        self.column_active = Gtk.ColumnViewColumn.new(_('Active'), self.factory_active)
        # ~ self.column_icon = Gtk.ColumnViewColumn.new("Icon", self.factory_icon)
        self.column_icon_type = Gtk.ColumnViewColumn.new(_('Type'), self.factory_icon_type)
        self.column_group = Gtk.ColumnViewColumn.new(_('Group'), self.factory_group)
        self.column_sentby = Gtk.ColumnViewColumn.new(_('Sent by'), self.factory_sentby)
        self.column_sentto = Gtk.ColumnViewColumn.new(_('Sent to'), self.factory_sentto)
        self.column_purpose = Gtk.ColumnViewColumn.new(_('Purpose'), self.factory_purpose)
        self.column_date = Gtk.ColumnViewColumn.new(_('Date'), self.factory_date)
        self.column_flag = Gtk.ColumnViewColumn.new(_('Country'), self.factory_flag)
        # ~ self.column_country = Gtk.ColumnViewColumn.new("Country", self.factory_country)

        self.cv.append_column(self.column_flag)
        self.cv.append_column(self.column_icon_type)
        self.cv.append_column(self.column_group)
        self.cv.append_column(self.column_purpose)
        self.cv.append_column(self.column_title)
        self.cv.append_column(self.column_subtitle)
        self.cv.append_column(self.column_sentby)
        self.cv.append_column(self.column_sentto)
        self.cv.append_column(self.column_date)
        # ~ self.cv.append_column(self.column_country)
        self.column_sentto.set_expand(False)
        self.column_sentby.set_expand(False)
        self.column_title.set_expand(False)

        # Sorting
        self.prop_group_sorter = Gtk.CustomSorter.new(sort_func=self._on_sort_string_func, user_data='group')
        self.prop_purpose_sorter = Gtk.CustomSorter.new(sort_func=self._on_sort_string_func, user_data='purpose')
        self.prop_sentby_sorter = Gtk.CustomSorter.new(sort_func=self._on_sort_string_func, user_data='sentby_dsc')
        self.prop_concept_sorter = Gtk.CustomSorter.new(sort_func=self._on_sort_string_func, user_data='subtitle')
        self.prop_sentto_sorter = Gtk.CustomSorter.new(sort_func=self._on_sort_string_func, user_data='sentto_dsc')
        self.prop_date_sorter = Gtk.CustomSorter.new(sort_func=self._on_sort_string_func, user_data='date')
        self.prop_flag_sorter = Gtk.CustomSorter.new(sort_func=self._on_sort_string_func, user_data='country')
        # ~ self.prop_country_sorter = Gtk.CustomSorter.new(sort_func=self._on_sort_string_func, user_data='country')
        self.column_group.set_sorter(self.prop_group_sorter)
        self.column_purpose.set_sorter(self.prop_purpose_sorter)
        self.column_sentby.set_sorter(self.prop_sentby_sorter)
        self.column_subtitle.set_sorter(self.prop_concept_sorter)
        self.column_sentto.set_sorter(self.prop_sentto_sorter)
        self.column_date.set_sorter(self.prop_date_sorter)
        self.column_flag.set_sorter(self.prop_flag_sorter)
        # ~ self.column_country.set_sorter(self.prop_country_sorter)

        # Default sorting by date
        self.cv.sort_by_column(self.column_date, Gtk.SortType.DESCENDING)

    def _on_factory_setup_subtitle(self, factory, list_item):
        box = ColLabel()
        list_item.set_child(box)

    def _on_factory_bind_subtitle(self, factory, list_item):
        box = list_item.get_child()
        item = list_item.get_item()
        label = box.get_first_child()
        # ~ label.set_markup("<b>%s</b>" % item.subtitle)
        # ~ label.set_ellipsize(True)
        # ~ label.set_property('ellipsize', Pango.EllipsizeMode.MIDDLE)
        if item.active:
            label.set_markup(f"<b>{item.subtitle}</b>")
        else:
            label.set_markup(f"<span color='red'><b>{item.subtitle}</b></span>")
            label.get_style_context().add_class(class_name='destructive-action')

    def _on_factory_setup_active(self, factory, list_item):
        box = ColCheck()
        list_item.set_child(box)
        # ~ button = box.get_first_child()

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
        # ~ box = list_item.get_child()
        # ~ item = list_item.get_item()
        # ~ icon = box.get_first_child()
        pass

    def _on_factory_setup_icon_type(self, factory, list_item):
        box = ColIcon()
        list_item.set_child(box)

    def _on_factory_bind_icon_type(self, factory, list_item):
        """To be subclassed"""
        box = list_item.get_child()
        icon = box.get_first_child()
        item = list_item.get_item()
        gicon = self.srvicm.get_mimetype_icon(item.id)
        if gicon is not None:
            icon.set_from_gicon(gicon)
            icon.set_pixel_size(36)

    def _on_factory_setup_country(self, factory, list_item):
        box = ColLabel()
        list_item.set_child(box)

    def _on_factory_bind_country(self, factory, list_item):
        box = list_item.get_child()
        item = list_item.get_item()
        label = box.get_first_child()
        country = item.country_dsc
        label.set_markup(country)

    def _on_factory_setup_group(self, factory, list_item):
        box = ColLabel()
        list_item.set_child(box)

    def _on_factory_bind_group(self, factory, list_item):
        box = list_item.get_child()
        item = list_item.get_item()
        label = box.get_first_child()
        group = item.group_dsc
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
        label.set_ellipsize(True)
        label.set_property('ellipsize', Pango.EllipsizeMode.MIDDLE)

    def _on_factory_setup_sentto(self, factory, list_item):
        box = ColLabel()
        list_item.set_child(box)

    def _on_factory_bind_sentto(self, factory, list_item):
        box = list_item.get_child()
        item = list_item.get_item()
        label = box.get_first_child()
        label.set_markup(item.sentto_dsc)
        label.set_ellipsize(True)
        label.set_property('ellipsize', Pango.EllipsizeMode.MIDDLE)

    def _on_factory_setup_purpose(self, factory, list_item):
        box = ColLabel()
        list_item.set_child(box)

    def _on_factory_bind_purpose(self, factory, list_item):
        box = list_item.get_child()
        item = list_item.get_item()
        label = box.get_first_child()
        purpose = item.purpose_dsc
        label.set_markup(purpose)

    def _on_factory_setup_flag(self, factory, list_item):
        box = ColIcon()
        list_item.set_child(box)

    def _on_factory_bind_flag(self, factory, list_item):
        box = list_item.get_child()
        box.set_halign(Gtk.Align.CENTER)
        item = list_item.get_item()
        icon = box.get_first_child()
        code = item.country
        icon.set_from_icon_name(code)
        icon.set_pixel_size(36)


class MiAZColumnViewCountry(MiAZColumnViewSelector):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewCountry'

    def __init__(self, app):
        super().__init__(app, item_type=Country)
        factory_flag = Gtk.SignalListItemFactory()
        factory_flag.connect("setup", self._on_factory_setup_flag)
        factory_flag.connect("bind", self._on_factory_bind_flag)
        self.column_flag = Gtk.ColumnViewColumn.new(_('Country'), factory_flag)
        self.cv.append_column(self.column_flag)
        self.cv.append_column(self.column_id)
        self.cv.append_column(self.column_title)

    def _on_factory_setup_flag(self, factory, list_item):
        box = ColIcon()
        list_item.set_child(box)

    def _on_factory_bind_flag(self, factory, list_item):
        ENV = self.app.get_env()
        box = list_item.get_child()
        country = list_item.get_item()
        icon = box.get_first_child()
        flag = os.path.join(ENV['GPATH']['FLAGS'], f"{country.id}.svg")
        if not os.path.exists(flag):
            flag = os.path.join(ENV['GPATH']['FLAGS'], "__.svg")
        icon.set_from_file(flag)
        icon.set_pixel_size(36)


class MiAZColumnViewDocuments(MiAZColumnView):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewDocuments'

    def __init__(self, app):
        super().__init__(app, item_type=File)
        self.cv.append_column(self.column_id)
        self.column_id.set_title(_('File'))
        self.column_id.set_expand(False)
        self.column_id.set_visible(False)
        self.cv.append_column(self.column_title)
        self.column_title.set_title(_('Document'))
        self.column_title.set_expand(True)


class MiAZColumnViewRepo(MiAZColumnViewSelector):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewRepo'

    def __init__(self, app):
        super().__init__(app, item_type=Repository)
        self.cv.append_column(self.column_id)
        self.column_title.set_title(_('Repo Id'))
        self.cv.append_column(self.column_title)
        self.column_title.set_title(_('Directory'))


class MiAZColumnViewGroup(MiAZColumnViewSelector):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewGroup'

    def __init__(self, app):
        super().__init__(app, item_type=Group)
        self.cv.append_column(self.column_id)
        self.column_title.set_title(_('Group Id'))
        self.cv.append_column(self.column_title)
        self.column_title.set_title(_('Description'))
        self.selection.connect("selection-changed", self._on_selection_change)

    def _on_selection_change(self, *args):
        pass


class MiAZColumnViewProject(MiAZColumnViewSelector):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewProject'

    def __init__(self, app):
        super().__init__(app, item_type=Project)
        self.cv.append_column(self.column_id)
        self.column_title.set_title(_('Project Id'))
        self.cv.append_column(self.column_title)
        self.column_title.set_title(_('Description'))


class MiAZColumnViewPurpose(MiAZColumnViewSelector):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewPurpose'

    def __init__(self, app):
        super().__init__(app, item_type=Purpose)
        self.cv.append_column(self.column_id)
        self.column_title.set_title(_('Purpose Id'))
        self.cv.append_column(self.column_title)
        self.column_title.set_title(_('Description'))

class MiAZColumnViewConcept(MiAZColumnViewSelector):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewConcept'

    def __init__(self, app):
        super().__init__(app, item_type=Concept)
        self.cv.append_column(self.column_id)
        self.column_title.set_title(_('Concept Id'))
        self.cv.append_column(self.column_title)
        self.column_title.set_title(_('Concept'))


class MiAZColumnViewPerson(MiAZColumnViewSelector):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewPerson'

    def __init__(self, app):
        super().__init__(app, item_type=Person)
        self.cv.append_column(self.column_id)
        self.column_id.set_title(_('Initials'))
        self.cv.append_column(self.column_title)
        self.column_title.set_title(_('Full name'))


class MiAZColumnViewMassRename(MiAZColumnView):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewMassRename'

    def __init__(self, app):
        super().__init__(app, item_type=File)
        self.cv.append_column(self.column_id)
        self.column_id.set_title(_('Source'))
        self.column_id.set_expand(True)
        self.cv.append_column(self.column_title)
        self.column_title.set_title(_('Target'))
        self.column_title.set_expand(True)


class MiAZColumnViewMassDelete(MiAZColumnView):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewMassDelete'

    def __init__(self, app):
        super().__init__(app, item_type=File)
        self.cv.append_column(self.column_id)
        self.column_id.set_title(_('Filename'))
        self.column_id.set_expand(False)
        self.column_id.set_visible(False)
        self.cv.append_column(self.column_title)
        self.column_title.set_title(_('Document'))
        self.column_title.set_expand(True)


class MiAZColumnViewMassProject(MiAZColumnView):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewMassProject'

    def __init__(self, app):
        super().__init__(app, item_type=File)
        self.cv.append_column(self.column_id)
        self.column_id.set_title(_('Document'))
        self.column_id.set_expand(False)
        self.column_id.set_visible(True)
        self.cv.append_column(self.column_title)
        self.column_title.set_title(_('Projects already assigned'))
        self.column_title.set_expand(True)


class MiAZColumnViewPlugin(MiAZColumnViewSelector):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewPlugin'

    def __init__(self, app):
        super().__init__(app, item_type=Plugin)
        self.cv.append_column(self.column_id)
        self.column_id.set_title(_('Plugin'))
        self.cv.append_column(self.column_title)
        self.column_title.set_title(_('Description'))
        self.column_title.set_expand(True)
