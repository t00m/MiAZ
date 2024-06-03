#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: export2csv.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items to CSV
"""

import os
import tempfile
from datetime import datetime
from gettext import gettext as _

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Peas

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import MiAZItem, File, Group, Person, Country, Purpose, Concept, SentBy, SentTo, Date, Extension, Project, Repository
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries
from MiAZ.frontend.desktop.widgets.configview import MiAZGroups
from MiAZ.frontend.desktop.widgets.configview import MiAZPeople
from MiAZ.frontend.desktop.widgets.configview import MiAZPurposes
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentBy
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentTo
from MiAZ.frontend.desktop.widgets.configview import MiAZProjects
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewWorkspace
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassRename
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassDelete
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassProject

Field = {}
Field[Date] = 0
Field[Country] = 1
Field[Group] = 2
Field[SentBy] = 3
Field[Purpose] = 4
Field[SentTo] = 6

Configview = {}
Configview['Country'] = MiAZCountries
Configview['Group'] = MiAZGroups
Configview['Purpose'] = MiAZPurposes
Configview['SentBy'] = MiAZPeopleSentBy
Configview['SentTo'] = MiAZPeopleSentTo
Configview['Project'] = MiAZProjects
Configview['Date'] = Gtk.Calendar


class MiAZToolbarProjectMgtPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZMassRenamingPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = MiAZLog('Plugin.MassRename')

    def do_activate(self):
        API = self.object
        self.app = API.app
        self.actions = self.app.get_service('actions')
        self.backend = self.app.get_service('backend')
        self.factory = self.app.get_service('factory')
        self.config = self.backend.get_config()
        self.util = self.app.get_service('util')
        self.repository = self.app.get_service('repo')
        self.workspace = API.app.get_widget('workspace')
        self.workspace.connect('workspace-loaded', self.add_menuitem)


    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")
        API = self.object

    def add_menuitem(self, *args):
        if self.app.get_widget('workspace-menu-selection-menu-massrename') is None:
            section_common_in = self.app.get_widget('workspace-menu-selection-section-common-in')
            submenu_massrename = Gio.Menu.new()
            menu_massrename = Gio.MenuItem.new_submenu(
                label = _('Mass renaming of...'),
                submenu = submenu_massrename,
            )
            section_common_in.append_item(menu_massrename)
            fields = [Date, Country, Group, SentBy, Purpose, SentTo]
            for item_type in fields:
                i_type = item_type.__gtype_name__
                i_title = _(item_type.__title__)
                menuitem = self.factory.create_menuitem('rename_%s' % i_type.lower(), '...%s' % i_title.lower(), self.document_rename_multiple, item_type, [])
                submenu_massrename.append_item(menuitem)
            self.app.add_widget('workspace-menu-selection-menu-massrename', menu_massrename)

    def document_rename_multiple(self, action, data, item_type):
        def update_columnview(dropdown, gparamobj, columnview, item_type, items):
            i_type = item_type.__gtype_name__
            i_title = _(item_type.__title__)
            citems = []
            for item in items:
                try:
                    source = item.id
                    name, ext = self.util.filename_details(source)
                    n = Field[item_type]
                    tmpfile = name.split('-')
                    tmpfile[n] = dropdown.get_selected_item().id
                    filename = "%s.%s" % ('-'.join(tmpfile), ext)
                    target = os.path.join(os.path.dirname(source), filename)
                    txtId = os.path.basename(source)
                    txtTitle = os.path.basename(target)
                    citems.append(File(id=txtId, title=txtTitle))
                except Exception as error:
                    # FIXME: AtributeError: 'NoneType' object has no attribute 'id'
                    # It happens when managing resources from inside the dialog
                    self.log.error(error)
                    pass
            columnview.update(citems)

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

        def dialog_response(dialog, response, dropdown, item_type, items):
            if response == Gtk.ResponseType.ACCEPT:
                title = _(item_type.__title__)
                for item in items:
                    bsource = item.id
                    name, ext = self.util.filename_details(bsource)
                    n = Field[item_type]
                    tmpfile = name.split('-')
                    tmpfile[n] = dropdown.get_selected_item().id
                    btarget = "%s.%s" % ('-'.join(tmpfile), ext)
                    source = os.path.join(self.repository.docs, bsource)
                    target = os.path.join(self.repository.docs, btarget)
                    self.util.filename_rename(source, target)
            dialog.destroy()

        def dialog_response_date(dialog, response, calendar, items):
            if response == Gtk.ResponseType.ACCEPT:
                adate = calendar.get_date()
                y = "%04d" % adate.get_year()
                m = "%02d" % adate.get_month()
                d = "%02d" % adate.get_day_of_month()
                sdate = "%s%s%s" % (y, m, d)
                for item in items:
                    bsource = os.path.basename(item.id)
                    name, ext = self.util.filename_details(bsource)
                    lname = name.split('-')
                    lname[0] = sdate
                    btarget = "%s.%s" % ('-'.join(lname), ext)
                    source = os.path.join(self.repository.docs, bsource)
                    target = os.path.join(self.repository.docs, btarget)
                    self.util.filename_rename(source, target)
            dialog.destroy()

        items = self.workspace.get_selected_items()
        if item_type != Date:
            i_type = item_type.__gtype_name__
            i_title = _(item_type.__title__)
            box = self.factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
            label = self.factory.create_label(_('Rename %d files by setting the field <b>%s</b> to:\n') % (len(items), i_title))
            dropdown = self.factory.create_dropdown_generic(item_type)
            btnManage = self.factory.create_button('miaz-res-manage', '')
            btnManage.connect('clicked', self.actions.manage_resource, Configview[i_type](self.app))
            frame = Gtk.Frame()
            cv = MiAZColumnViewMassRename(self.app)
            cv.get_style_context().add_class(class_name='caption')
            cv.set_hexpand(True)
            cv.set_vexpand(True)
            dropdown.connect("notify::selected-item", update_columnview, cv, item_type, items)
            self.config[i_type].connect('used-updated', self.actions.dropdown_populate, dropdown, item_type, False)
            self.actions.dropdown_populate(self.config[i_type], dropdown, item_type, any_value=False)
            frame.set_child(cv)
            box.append(label)
            hbox = self.factory.create_box_horizontal()
            hbox.append(dropdown)
            hbox.append(btnManage)
            box.append(hbox)
            box.append(frame)
            dialog = self.factory.create_dialog_question(self.app.win, _('Mass renaming'), box, width=1024, height=600)
            dialog.connect('response', dialog_response, dropdown, item_type, items)
            dialog.show()
        else:
            box = self.factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
            hbox = self.factory.create_box_horizontal()
            label = Gtk.Label()
            calendar = Gtk.Calendar()
            btnDate = self.factory.create_button_popover(icon_name='miaz-res-date', widgets=[calendar])
            hbox.append(btnDate)
            hbox.append(label)
            frame = Gtk.Frame()
            cv = MiAZColumnViewMassRename(self.app)
            cv.get_style_context().add_class(class_name='caption')
            cv.set_hexpand(True)
            cv.set_vexpand(True)
            frame.set_child(cv)
            box.append(hbox)
            box.append(frame)
            sdate = datetime.strftime(datetime.now(), '%Y%m%d')
            iso8601 = "%sT00:00:00Z" % sdate
            calendar.connect('day-selected', calendar_day_selected, label, cv, items)
            calendar.select_day(GLib.DateTime.new_from_iso8601(iso8601))
            calendar.emit('day-selected')
            dialog = self.factory.create_dialog_question(self.app.win, _('Mass renaming'), box, width=640, height=480)
            dialog.connect('response', dialog_response_date, calendar, items)
            dialog.show()

