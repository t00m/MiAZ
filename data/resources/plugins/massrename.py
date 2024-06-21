#!/usr/bin/python3
# pylint: disable=E1101, R0914

"""
# File: export2csv.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items to CSV
"""

import os
from datetime import datetime
from gettext import gettext as _

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Peas

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import File, Group, Country, Purpose, SentBy, SentTo, Date
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries
from MiAZ.frontend.desktop.widgets.configview import MiAZGroups
from MiAZ.frontend.desktop.widgets.configview import MiAZPurposes
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentBy
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentTo
from MiAZ.frontend.desktop.widgets.configview import MiAZProjects
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassRename

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
        self.app = None

    def do_activate(self):
        self.app = self.object.app
        workspace = self.app.get_widget('workspace')
        workspace.connect('workspace-loaded', self.add_menuitem)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")

    def add_menuitem(self, *args):
        if self.app.get_widget('workspace-menu-selection-menu-massrename') is None:
            factory = self.app.get_service('factory')
            section_common_in = self.app.get_widget('workspace-menu-selection-section-common-in')
            submenu_massrename = Gio.Menu.new()
            menu_massrename = Gio.MenuItem.new_submenu(
                label=_('Mass renaming of...'),
                submenu=submenu_massrename,
            )
            section_common_in.append_item(menu_massrename)
            fields = [Date, Country, Group, SentBy, Purpose, SentTo]
            for item_type in fields:
                i_type = item_type.__gtype_name__
                i_title = _(item_type.__title__)
                menuitem = factory.create_menuitem(f'rename_{i_type.lower()}', f'...{i_title.lower()}', self.document_rename_multiple, item_type, [])
                submenu_massrename.append_item(menuitem)
            self.app.add_widget('workspace-menu-selection-menu-massrename', menu_massrename)

    def document_rename_multiple(self, action, data, item_type):
        actions = self.app.get_service('actions')
        config = self.app.get_config_dict()
        factory = self.app.get_service('factory')
        repository = self.app.get_service('repo')
        util = self.app.get_service('util')
        workspace = self.app.get_widget('workspace')

        def update_columnview(dropdown, gparamobj, columnview, item_type, items):
            util = self.app.get_service('util')
            citems = []
            for item in items:
                try:
                    source = item.id
                    name, ext = util.filename_details(source)
                    n = Field[item_type]
                    tmpfile = name.split('-')
                    tmpfile[n] = dropdown.get_selected_item().id
                    filename = f"{'-'.join(tmpfile)}.{ext}"
                    target = os.path.join(os.path.dirname(source), filename)
                    txtId = os.path.basename(source)
                    txtTitle = os.path.basename(target)
                    citems.append(File(id=txtId, title=txtTitle))
                except AttributeError as error:
                    # FIXME: AtributeError: 'NoneType' object has no attribute 'id'
                    # It happens when managing resources from inside the dialog
                    self.log.error(error)
            columnview.update(citems)

        def calendar_day_selected(calendar, label, columnview, items):
            util = self.app.get_service('util')
            adate = calendar.get_date()
            y = f"{adate.get_year():04d}"
            m = f"{adate.get_month():02d}"
            d = f"{adate.get_day_of_month():02d}"
            sdate = f"{y}{m}{d}"
            ddate = datetime.strptime(sdate, '%Y%m%d')
            label.set_text(ddate.strftime('%A, %B %d %Y'))
            citems = []
            for item in items:
                source = os.path.basename(item.id)
                name, ext = util.filename_details(source)
                lname = name.split('-')
                lname[0] = sdate
                target = f"{'-'.join(lname)}.{ext}"
                citems.append(File(id=source, title=target))
            columnview.update(citems)

        def dialog_response(dialog, response, dropdown, item_type, items):
            util = self.app.get_service('util')
            repository = self.app.get_service('repo')
            if response == Gtk.ResponseType.ACCEPT:
                for item in items:
                    bsource = item.id
                    name, ext = util.filename_details(bsource)
                    n = Field[item_type]
                    tmpfile = name.split('-')
                    tmpfile[n] = dropdown.get_selected_item().id
                    btarget = f"{'-'.join(tmpfile)}.{ext}"
                    source = os.path.join(repository.docs, bsource)
                    target = os.path.join(repository.docs, btarget)
                    util.filename_rename(source, target)
            dialog.destroy()

        def dialog_response_date(dialog, response, calendar, items):
            if response == Gtk.ResponseType.ACCEPT:
                adate = calendar.get_date()
                y = f"{adate.get_year():04d}"
                m = f"{adate.get_month():02d}"
                d = f"{adate.get_day_of_month():02d}"
                sdate = f"{y}{m}{d}"
                for item in items:
                    bsource = os.path.basename(item.id)
                    name, ext = util.filename_details(bsource)
                    lname = name.split('-')
                    lname[0] = sdate
                    btarget = f"{'-'.join(lname)}.{ext}"
                    source = os.path.join(repository.docs, bsource)
                    target = os.path.join(repository.docs, btarget)
                    util.filename_rename(source, target)
            dialog.destroy()

        items = workspace.get_selected_items()
        if item_type != Date:
            i_type = item_type.__gtype_name__
            i_title = item_type.__title__
            i_title_plural = item_type.__title_plural__
            box = factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
            label = factory.create_label(_(f'Rename {len(items)} files by setting the field <b>{i_title}</b> to:\n'))
            dropdown = factory.create_dropdown_generic(item_type)
            icon_name = f'com.github.t00m.MiAZ-res-{i_title_plural.lower()}'
            self.log.debug(icon_name)
            btnManage = factory.create_button(icon_name=icon_name, title='')
            btnManage.connect('clicked', actions.manage_resource, Configview[i_type](self.app))
            frame = Gtk.Frame()
            cv = MiAZColumnViewMassRename(self.app)
            cv.get_style_context().add_class(class_name='caption')
            cv.set_hexpand(True)
            cv.set_vexpand(True)
            dropdown.connect("notify::selected-item", update_columnview, cv, item_type, items)
            config[i_type].connect('used-updated', actions.dropdown_populate, dropdown, item_type, False)
            actions.dropdown_populate(config[i_type], dropdown, item_type, any_value=False)
            frame.set_child(cv)
            box.append(label)
            hbox = factory.create_box_horizontal()
            hbox.append(dropdown)
            hbox.append(btnManage)
            box.append(hbox)
            box.append(frame)
            window = self.app.get_widget('window')
            dialog = factory.create_dialog_question(window, _('Mass renaming'), box, width=1024, height=600)
            dialog.connect('response', dialog_response, dropdown, item_type, items)
            dialog.show()
        else:
            box = factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
            hbox = factory.create_box_horizontal()
            label = Gtk.Label()
            calendar = Gtk.Calendar()
            btnDate = factory.create_button_popover(icon_name='com.github.t00m.MiAZ-res-date', widgets=[calendar])
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
            iso8601 = f"{sdate}T00:00:00Z"
            calendar.connect('day-selected', calendar_day_selected, label, cv, items)
            calendar.select_day(GLib.DateTime.new_from_iso8601(iso8601))
            calendar.emit('day-selected')
            window = self.app.get_widget('window')
            dialog = factory.create_dialog_question(window, _('Mass renaming'), box, width=640, height=480)
            dialog.connect('response', dialog_response_date, calendar, items)
            dialog.show()
