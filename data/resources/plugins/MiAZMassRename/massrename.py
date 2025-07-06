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

from MiAZ.backend.status import MiAZStatus
from MiAZ.frontend.desktop.services.pluginsystem import MiAZPlugin
from MiAZ.backend.models import File, Group, Country, Purpose, SentBy, SentTo, Date
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries
from MiAZ.frontend.desktop.widgets.configview import MiAZGroups
from MiAZ.frontend.desktop.widgets.configview import MiAZPurposes
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentBy
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentTo
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassRename

plugin_info = {
        'Module':        'massrename',
        'Name':          'MiAZMassRename',
        'Loader':        'Python3',
        'Description':   _('Mass renaming of documents'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2025 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'http://github.com/t00m/MiAZ/README.adoc',
        'Version':       '0.5',
        'Category':      _('Data Management'),
        'Subcategory':   _('Batch mode')
    }

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
Configview['Date'] = Gtk.Calendar


class MiAZMassRenamingPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZMassRenamingPlugin'
    object = GObject.Property(type=GObject.Object)
    plugin = None

    def do_activate(self):
        """Plugin activation"""
        # Setup plugin
        ## Get pointer to app
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)

        ## Initialize plugin
        self.plugin.register(self, plugin_info)

        ## Get logger
        self.log = self.plugin.get_logger()

        ## Get services
        self.actions = self.app.get_service('actions')
        self.config = self.app.get_config_dict()
        self.factory = self.app.get_service('factory')
        self.repository = self.app.get_service('repo')
        self.util = self.app.get_service('util')
        self.workspace = self.app.get_widget('workspace')
        self.srvdlg = self.app.get_service('dialogs')

        ## Connect signals
        self.workspace.connect('workspace-loaded', self.startup)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")

    def startup(self, *args):
        if not self.plugin.started():
            # Get root submenu
            category = plugin_info['Category']
            subcategory = plugin_info['Subcategory']
            submenu = self.app.install_plugin_menu(category, subcategory)

            # Create plugin submenu
            menuitem_name = f'plugin-menuitem-{self.plugin.get_name()}'
            menuitem = self.app.get_widget(menuitem_name)
            if menuitem is None:
                submenu_massrename = Gio.Menu.new()
                menu_massrename = Gio.MenuItem.new_submenu(
                        label=_('Mass renaming'),
                        submenu=submenu_massrename,
                    )
                self.app.add_widget(menuitem_name, menu_massrename)
                fields = [Date, Country, Group, SentBy, Purpose, SentTo]
                for item_type in fields:
                    i_type = _(item_type.__gtype_name__)
                    i_title = _(item_type.__title__)
                    label = _('... of {title}').format(title=i_title.lower())
                    name = f'rename_{i_type.lower()}'
                    menuitem = self.factory.create_menuitem(name=name, label=label, callback=self.document_rename_multiple, data=item_type, shortcuts=None)
                    submenu_massrename.append_item(menuitem)

                # Attach plugin submenu to root submenu
                submenu.append_item(menu_massrename)

            # Plugin configured
            self.plugin.set_started(started=True)

    def document_rename_multiple(self, action, data, item_type):
        """
        """

        def update_columnview(dropdown, gparamobj, columnview, item_type, items):
            self.util = self.app.get_service('util')
            citems = []
            for item in items:
                try:
                    source = item.id
                    name, ext = self.util.filename_details(source)
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
            self.util = self.app.get_service('util')
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
                name, ext = self.util.filename_details(source)
                lname = name.split('-')
                lname[0] = sdate
                target = f"{'-'.join(lname)}.{ext}"
                citems.append(File(id=source, title=target))
            columnview.update(citems)

        def dialog_response(dialog, response, dropdown, item_type, items):
            if response == 'apply':
                self.app.set_status(MiAZStatus.BUSY)
                for item in items:
                    bsource = item.id
                    name, ext = self.util.filename_details(bsource)
                    n = Field[item_type]
                    tmpfile = name.split('-')
                    tmpfile[n] = dropdown.get_selected_item().id
                    btarget = f"{'-'.join(tmpfile)}.{ext}"
                    source = os.path.join(self.repository.docs, bsource)
                    target = os.path.join(self.repository.docs, btarget)
                    self.util.filename_rename(source, target)
                self.app.set_status(MiAZStatus.RUNNING)

        def dialog_response_date(dialog, response, calendar, items):
            if response == 'apply':
                adate = calendar.get_date()
                y = f"{adate.get_year():04d}"
                m = f"{adate.get_month():02d}"
                d = f"{adate.get_day_of_month():02d}"
                sdate = f"{y}{m}{d}"
                self.app.set_status(MiAZStatus.BUSY)
                for item in items:
                    bsource = os.path.basename(item.id)
                    name, ext = self.util.filename_details(bsource)
                    lname = name.split('-')
                    lname[0] = sdate
                    btarget = f"{'-'.join(lname)}.{ext}"
                    source = os.path.join(self.repository.docs, bsource)
                    target = os.path.join(self.repository.docs, btarget)
                    self.util.filename_rename(source, target)
                self.app.set_status(MiAZStatus.RUNNING)

        items = self.workspace.get_selected_items()
        if self.actions.stop_if_no_items():
            self.log.debug("No items selected")
            return

        if item_type != Date:
            i_type = item_type.__gtype_name__
            i_title = item_type.__title__
            i_title_plural = item_type.__title_plural__
            box = self.factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
            label = self.factory.create_label(_(f'Rename {len(items)} files by setting the field <b>{i_title}</b> to:\n'))
            dropdown = self.factory.create_dropdown_generic(item_type)
            icon_name = f'io.github.t00m.MiAZ-res-{i_title_plural.lower()}'
            self.log.debug(icon_name)
            btnManage = self.factory.create_button(icon_name=icon_name, title='')
            btnManage.connect('clicked', self.actions.manage_resource, Configview[i_type](self.app))
            frame = Gtk.Frame()
            cv = MiAZColumnViewMassRename(self.app)
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
            window = self.app.get_widget('window')
            dialog = self.srvdlg.show_action(title=_('Mass renaming'), widget=box, width=1024, height=600)
            dialog.connect('response', dialog_response, dropdown, item_type, items)
            dialog.present(window)
        else:
            box = self.factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
            hbox = self.factory.create_box_horizontal()
            label = Gtk.Label()
            calendar = Gtk.Calendar()
            btnDate = self.factory.create_button_popover(icon_name='io.github.t00m.MiAZ-res-date', widgets=[calendar])
            hbox.append(btnDate)
            hbox.append(label)
            frame = Gtk.Frame()
            cv = MiAZColumnViewMassRename(self.app)
            # ~ cv.get_style_context().add_class(class_name='caption')
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
            dialog = self.srvdlg.show_action(title=_('Mass renaming'), widget=box, width=640, height=480)
            dialog.connect('response', dialog_response_date, calendar, items)
            dialog.present(window)

