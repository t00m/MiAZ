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
from MiAZ.backend.models import MiAZItem
from MiAZ.backend.util import json_load
from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnView
from MiAZ.frontend.desktop.widgets.columnview import RowIcon
from MiAZ.backend.models import Country, Group, Subgroup, Person, People, Purpose

class MiAZColumnViewCountry(MiAZColumnView):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewCountry'

    def __init__(self, app):
        super().__init__(app, item_type=Country)
        factory_flag = Gtk.SignalListItemFactory()
        factory_flag.connect("setup", self._on_factory_setup_flag)
        factory_flag.connect("bind", self._on_factory_bind_flag)
        self.column_flag = Gtk.ColumnViewColumn.new("Flag", factory_flag)
        self.cv.append_column(self.column_flag)
        self.cv.append_column(self.column_id)
        self.cv.append_column(self.column_title)

    def _on_factory_setup_flag(self, factory, list_item):
        box = RowIcon()
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
        self.cv.append_column(self.column_title)
        self.column_title.set_title("Group")

class MiAZColumnViewSubgroup(MiAZColumnView):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewSubgroup'

    def __init__(self, app):
        super().__init__(app, item_type=Subgroup)
        self.cv.append_column(self.column_title)
        self.column_title.set_title("Subgroup")

class MiAZColumnViewPurpose(MiAZColumnView):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewPurpose'

    def __init__(self, app):
        super().__init__(app, item_type=Purpose)
        self.cv.append_column(self.column_title)
        self.column_title.set_title("Purpose")

class MiAZColumnViewPerson(MiAZColumnView):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewPerson'

    def __init__(self, app):
        super().__init__(app, item_type=Person)
        self.cv.append_column(self.column_id)
        self.cv.append_column(self.column_title)
        self.column_id.set_title("Initials")
        self.column_title.set_title("Full name")
