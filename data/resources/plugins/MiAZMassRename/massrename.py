#!/usr/bin/python3
# pylint: disable=E1101, R0914

"""
# File: massrename.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items to CSV
"""

import os
from datetime import datetime
from gettext import gettext as _

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin
from MiAZ.backend.models import File, Group, Country, Purpose, SentBy, SentTo, Date, Concept
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries
from MiAZ.frontend.desktop.widgets.configview import MiAZGroups
from MiAZ.frontend.desktop.widgets.configview import MiAZPurposes
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentBy
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentTo
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassRename

import sys
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
import concept_ops

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
        'Category':      'Data Management',
        'Subcategory':   'Batch mode'
    }

Field = {}
Field[Date] = 0
Field[Country] = 1
Field[Group] = 2
Field[SentBy] = 3
Field[Purpose] = 4
Field[Concept] = 5
Field[SentTo] = 6

Configview = {}
Configview['Country'] = MiAZCountries
Configview['Group'] = MiAZGroups
Configview['Purpose'] = MiAZPurposes
Configview['SentBy'] = MiAZPeopleSentBy
Configview['SentTo'] = MiAZPeopleSentTo
Configview['Date'] = Gtk.Calendar


class MiAZMassRenamingPlugin(MiAZExtension):
    __gtype_name__ = 'MiAZMassRenamingPlugin'
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
        if self.workspace.is_loaded():
            self.startup()
        else:
            self._startup_handler = self.workspace.connect('workspace-loaded', self.startup)

    def do_deactivate(self):
        if hasattr(self, '_startup_handler'):
            self.workspace.disconnect(self._startup_handler)
        self.plugin.set_started(False)

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

                # Concept is free-form, so it gets a transform tool instead of
                # a vocabulary dropdown.
                concept_item = self.factory.create_menuitem(
                    name='rename_concept',
                    label=_('... of concept'),
                    callback=self.document_rename_concept,
                    data=Concept,
                    shortcuts=None)
                submenu_massrename.append_item(concept_item)

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
                selected = dropdown.get_selected_item()
                if selected is None:
                    continue
                source = item.id
                name, ext = self.util.filename_details(source)
                n = Field[item_type]
                tmpfile = name.split('-')
                tmpfile[n] = selected.id
                filename = f"{'-'.join(tmpfile)}.{ext}"
                target = os.path.join(os.path.dirname(source), filename)
                txtId = os.path.basename(source)
                txtTitle = os.path.basename(target)
                citems.append(File(id=txtId, title=txtTitle))
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
                selected = dropdown.get_selected_item()
                if selected is None:
                    return
                # Do NOT toggle the app status to BUSY here. The workspace
                # skips its update while BUSY, and if any item in the batch
                # raised mid-loop the RUNNING reset would be missed, stranding
                # the app in BUSY and freezing every later view refresh. Each
                # filename_rename emits 'filename-renamed', which the workspace
                # already debounces into a single update, like the single
                # rename path. Skip files that cannot be renamed so one bad
                # name does not abort the rest of the batch.
                n = Field[item_type]
                for item in items:
                    bsource = item.id
                    name, ext = self.util.filename_details(bsource)
                    tmpfile = name.split('-')
                    if n >= len(tmpfile):
                        self.log.warning(f"Skipping '{bsource}': not enough fields to set {item_type.__gtype_name__}")
                        continue
                    tmpfile[n] = selected.id
                    btarget = f"{'-'.join(tmpfile)}.{ext}"
                    source = os.path.join(self.repository.docs, bsource)
                    target = os.path.join(self.repository.docs, btarget)
                    self.util.filename_rename(source, target)

        def dialog_response_date(dialog, response, calendar, items):
            if response == 'apply':
                adate = calendar.get_date()
                y = f"{adate.get_year():04d}"
                m = f"{adate.get_month():02d}"
                d = f"{adate.get_day_of_month():02d}"
                sdate = f"{y}{m}{d}"
                # See dialog_response: no BUSY juggling. The debounced
                # 'filename-renamed' signal refreshes the workspace once.
                for item in items:
                    bsource = os.path.basename(item.id)
                    name, ext = self.util.filename_details(bsource)
                    lname = name.split('-')
                    if not lname:
                        continue
                    lname[0] = sdate
                    btarget = f"{'-'.join(lname)}.{ext}"
                    source = os.path.join(self.repository.docs, bsource)
                    target = os.path.join(self.repository.docs, btarget)
                    self.util.filename_rename(source, target)

        items = self.workspace.get_selected_items()
        if self.actions.stop_if_no_items():
            self.log.debug("No items selected")
            return

        if item_type != Date:
            i_type = item_type.__gtype_name__
            i_title = item_type.__title__
            i_title_plural = item_type.__title_plural__
            box = self.factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
            label = self.factory.create_label(
                _('Rename {count} files by setting the field <b>{field}</b> to:\n')
                .format(count=len(items), field=i_title))
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

    def document_rename_concept(self, action, data, item_type):
        """Transform the free-form concept field of the selected documents."""
        items = self.workspace.get_selected_items()
        if self.actions.stop_if_no_items():
            self.log.debug("No items selected")
            return

        n = Field[Concept]
        op_keys = ['keep', 'remove', 'prefix', 'suffix', 'replace', 'case', 'set']
        op_labels = [_('Keep token(s)'), _('Remove token(s)'), _('Add prefix'),
                     _('Add suffix'), _('Find & replace'), _('Change case'),
                     _('Set value')]
        case_modes = ['upper', 'lower', 'title']

        entry_sep = Gtk.Entry(text='_')
        entry_positions = Gtk.Entry()
        entry_positions.set_placeholder_text(_('e.g. 2-3'))
        entry_text = Gtk.Entry()
        entry_find = Gtk.Entry()
        entry_find.set_placeholder_text(_('find'))
        entry_replace = Gtk.Entry()
        entry_replace.set_placeholder_text(_('replace with'))
        entry_value = Gtk.Entry()
        dd_case = Gtk.DropDown.new_from_strings([_('upper'), _('lower'), _('title')])
        dd_op = Gtk.DropDown.new_from_strings(op_labels)

        def labeled(text, widget):
            hbox = self.factory.create_box_horizontal(spacing=6)
            hbox.append(Gtk.Label(label=text))
            hbox.append(widget)
            return hbox

        box_positions = labeled(_('Positions'), entry_positions)
        box_sep = labeled(_('Separator'), entry_sep)
        box_text = labeled(_('Text'), entry_text)
        box_find = labeled(_('Find'), entry_find)
        box_replace = labeled(_('Replace'), entry_replace)
        box_case = labeled(_('Case'), dd_case)
        box_value = labeled(_('Value'), entry_value)

        def current_op():
            return op_keys[dd_op.get_selected()]

        def current_params():
            return {
                'sep': entry_sep.get_text() or '_',
                'positions': entry_positions.get_text(),
                'text': entry_text.get_text(),
                'find': entry_find.get_text(),
                'replace': entry_replace.get_text(),
                'mode': case_modes[dd_case.get_selected()],
                'value': entry_value.get_text(),
            }

        def target_basename(bsource, op, params):
            name, ext = self.util.filename_details(bsource)
            fields = name.split('-')
            if len(fields) != 7:
                return None
            new_concept = concept_ops.apply(op, fields[n], params)
            new_concept = self.util.valid_key(new_concept)
            if not new_concept:
                return None
            fields[n] = new_concept
            return f"{'-'.join(fields)}.{ext}"

        def update_visibility(*_a):
            op = current_op()
            box_positions.set_visible(op in ('keep', 'remove'))
            box_sep.set_visible(op in ('keep', 'remove', 'prefix', 'suffix'))
            box_text.set_visible(op in ('prefix', 'suffix'))
            box_find.set_visible(op == 'replace')
            box_replace.set_visible(op == 'replace')
            box_case.set_visible(op == 'case')
            box_value.set_visible(op == 'set')

        def refresh_preview(*_a):
            op = current_op()
            params = current_params()
            citems = []
            for item in items:
                bsource = item.id
                btarget = target_basename(bsource, op, params)
                title = btarget if btarget is not None else bsource
                citems.append(File(id=bsource, title=title))
            cv.update(citems)

        def dialog_response_concept(dialog, response):
            if response != 'apply':
                return
            op = current_op()
            params = current_params()
            renamed = 0
            skipped = 0
            for item in items:
                bsource = item.id
                btarget = target_basename(bsource, op, params)
                if btarget is None or btarget == bsource:
                    skipped += 1
                    continue
                source = os.path.join(self.repository.docs, bsource)
                target = os.path.join(self.repository.docs, btarget)
                if self.util.filename_rename(source, target):
                    renamed += 1
                else:
                    skipped += 1
            self.srvdlg.show_toast(
                _('Renamed {r}, skipped {s}').format(r=renamed, s=skipped))

        box = self.factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
        label = self.factory.create_label(
            _('Transform the <b>concept</b> of {count} files:\n')
            .format(count=len(items)))
        params_box = self.factory.create_box_horizontal(spacing=12)
        for child in (box_positions, box_sep, box_text, box_find,
                      box_replace, box_case, box_value):
            params_box.append(child)
        frame = Gtk.Frame()
        cv = MiAZColumnViewMassRename(self.app)
        cv.set_hexpand(True)
        cv.set_vexpand(True)
        frame.set_child(cv)
        box.append(label)
        box.append(dd_op)
        box.append(params_box)
        box.append(frame)

        dd_op.connect('notify::selected', update_visibility)
        dd_op.connect('notify::selected', refresh_preview)
        dd_case.connect('notify::selected', refresh_preview)
        for entry in (entry_sep, entry_positions, entry_text, entry_find,
                      entry_replace, entry_value):
            entry.connect('changed', refresh_preview)

        update_visibility()
        refresh_preview()
        window = self.app.get_widget('window')
        dialog = self.srvdlg.show_action(
            title=_('Mass renaming: concept'), widget=box, width=1024, height=600)
        dialog.connect('response', dialog_response_concept)
        dialog.present(window)

