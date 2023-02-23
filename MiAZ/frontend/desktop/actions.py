#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import glob
from datetime import datetime

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from MiAZ.backend.log import get_logger
from MiAZ.backend.models import MiAZItem, File, Group, Person, Country, Purpose, Concept, SentBy, SentTo, Date, Extension, Project
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries, MiAZGroups, MiAZPeople, MiAZPurposes, MiAZPeopleSentBy, MiAZPeopleSentTo, MiAZProjects
from MiAZ.frontend.desktop.widgets.rename import MiAZRenameDialog
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewWorkspace
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassRename
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassDelete
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassProject

# Conversion Item type to Field Number
Field = {}
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

class MiAZActions(GObject.GObject):
    def __init__(self, app):
        self.log = get_logger('MiAZActions')
        self.app = app
        self.backend = self.app.get_backend()
        self.util = self.backend.util

    def add_directory_to_repo(self, dialog, response):
        config = self.backend.repo_config()
        target_dir = config['dir_docs']
        if response == Gtk.ResponseType.ACCEPT:
            content_area = dialog.get_content_area()
            box = content_area.get_first_child()
            filechooser = box.get_first_child()
            toggle = box.get_last_child()
            recursive = toggle.get_active()
            gfile = filechooser.get_file()
            if gfile is not None:
                dirpath = gfile.get_path()
                self.log.debug("Walk directory %s recursively? %s", dirpath, recursive)
                if recursive:
                    files = self.util.get_files_recursively(dirpath)
                else:
                    files = glob.glob(os.path.join(dirpath, '*.*'))
                for source in files:
                    target = self.util.filename_normalize(source)
                    self.util.filename_copy(source, target)
        dialog.destroy()

    def add_file_to_repo(self, dialog, response):
        config = self.backend.repo_config()
        target_dir = config['dir_docs']
        if response == Gtk.ResponseType.ACCEPT:
            content_area = dialog.get_content_area()
            filechooser = content_area.get_last_child()
            gfile = filechooser.get_file()
            if gfile is not None:
                source = gfile.get_path()
                target = self.util.filename_normalize(source)
                self.util.filename_copy(source, target)
        dialog.destroy()

    def document_display(self, doc):
        self.log.debug("Displaying %s", doc)
        self.util.filename_display(doc)

    def document_delete(self, doc):
        self.log.debug("Deleting %s", doc)
        self.util.filename_delete(doc)

    def document_rename_single(self, doc):
        self.log.debug("Rename %s", doc)
        rename = self.app.get_rename_widget()
        rename.set_data(doc)
        self.app.show_stack_page_by_name('rename')

    def document_rename_multiple(self, item_type, items):

        def update_columnview(dropdown, gparamobj, columnview, item_type, items):
            i_type = item_type.__gtype_name__
            i_title = item_type.__title__
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
                    txtId = "<small>%s</small>" % os.path.basename(source)
                    txtTitle = "<small>%s</small>" % os.path.basename(target)
                    citems.append(File(id=txtId, title=txtTitle))
                except Exception as error:
                    # FIXME: AtributeError: 'NoneType' object has no attribute 'id'
                    # It happens when managing resources from inside the dialog
                    pass
            columnview.update(citems)

        def update_dropdown(config, dropdown, item_type, any_value):
            title = item_type.__gtype_name__
            self.dropdown_populate(dropdown, item_type, any_value=any_value)
            dropdown.set_selected(0)

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
                title = item_type.__title__
                for item in items:
                    source = item.id
                    name, ext = self.util.filename_details(source)
                    n = Field[item_type]
                    tmpfile = name.split('-')
                    tmpfile[n] = dropdown.get_selected_item().id
                    target = "%s.%s" % ('-'.join(tmpfile), ext)
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
                    source = os.path.basename(item.id)
                    name, ext = self.util.filename_details(source)
                    lname = name.split('-')
                    lname[0] = sdate
                    target = "%s.%s" % ('-'.join(lname), ext)
                    self.util.filename_rename(source, target)
            dialog.destroy()

        self.factory = self.app.get_factory()
        self.config = self.backend.conf

        if item_type != Date:
            i_type = item_type.__gtype_name__
            i_title = item_type.__title__
            self.log.debug("Rename %s for:", i_title)
            box = self.factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
            label = self.factory.create_label('Rename %d files by setting the field <b>%s</b> to:\n' % (len(items), i_title))
            dropdown = self.factory.create_dropdown_generic(item_type)
            btnManage = self.factory.create_button('miaz-res-manage', '')
            btnManage.connect('clicked', self.on_resource_manage, Configview[i_type](self.app))
            frame = Gtk.Frame()
            cv = MiAZColumnViewMassRename(self.app)
            cv.get_style_context().add_class(class_name='monospace')
            cv.set_hexpand(True)
            cv.set_vexpand(True)
            dropdown.connect("notify::selected-item", update_columnview, cv, item_type, items)
            self.config[i_type].connect('used-updated', update_dropdown, dropdown, item_type, False)
            self.dropdown_populate(dropdown, item_type, any_value=False)
            frame.set_child(cv)
            box.append(label)
            hbox = self.factory.create_box_horizontal()
            hbox.append(dropdown)
            hbox.append(btnManage)
            box.append(hbox)
            box.append(frame)
            dialog = self.factory.create_dialog_question(self.app.win, 'Mass renaming', box, width=1024, height=600)
            dialog.connect('response', dialog_response, dropdown, item_type, items)
            dialog.show()
        else:
            self.log.debug("FIXME! Not implemented")
            box = self.factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
            hbox = self.factory.create_box_horizontal()
            label = Gtk.Label()
            calendar = Gtk.Calendar()
            btnDate = self.factory.create_button_popover(icon_name='miaz-res-date', widgets=[calendar])
            hbox.append(btnDate)
            hbox.append(label)
            frame = Gtk.Frame()
            cv = MiAZColumnViewMassRename(self.app)
            cv.get_style_context().add_class(class_name='monospace')
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
            dialog = self.factory.create_dialog_question(self.app.win, 'Mass renaming', box, width=640, height=480)
            dialog.connect('response', dialog_response_date, calendar, items)
            dialog.show()

    def select_dropdown_item(self, dropdown, key):
        found = False
        model = dropdown.get_model()
        n = 0
        for item in model:
            if item.id.upper() == key.upper():
                dropdown.set_selected(n)
                found = True
            n += 1
        if not found:
            dropdown.set_selected(0)

    def dropdown_populate(self, dropdown, item_type, keyfilter = False, intkeys=[], any_value=True, none_value=False):
        model = dropdown.get_model()
        config = self.app.get_config(item_type.__gtype_name__)
        items = config.load(config.used)
        title = item_type.__gtype_name__

        items = config.load(config.used)

        model.remove_all()

        if any_value:
            model.append(item_type(id='Any', title='Any'))

        if none_value:
            model.append(item_type(id='None', title='None'))

        for key in items:
            title = items[key]
            if len(title) == 0:
                title = key
            model.append(item_type(id=key, title=title))


    def on_import_directory(self, *args):
        self.factory = self.app.get_factory()
        filechooser = self.factory.create_filechooser(
                    parent=self.app.win,
                    title='Import a directory',
                    target = 'FOLDER',
                    callback = self.add_directory_to_repo
                    )
        filechooser.show()

    def on_import_file(self, *args):
        self.factory = self.app.get_factory()
        filechooser = self.factory.create_filechooser(
                    parent=self.app.win,
                    title='Import a single file',
                    target = 'FILE',
                    callback = self.add_file_to_repo
                    )
        filechooser.show()

    def on_resource_manage(self, widget: Gtk.Widget, selector: Gtk.Widget):
        factory = self.app.get_factory()
        box = factory.create_box_vertical(spacing=0, vexpand=True, hexpand=True)
        box.append(selector)
        config_for = selector.get_config_for()
        selector.set_vexpand(True)
        selector.update()
        dialog = factory.create_dialog(self.app.win, 'Manage %s' % config_for, box, 800, 600)
        dialog.show()


    def _on_mass_action_project_dialog(self, *args):
        def update_dropdown(config, dropdown, item_type, any_value):
            title = item_type.__gtype_name__
            self.actions.dropdown_populate(dropdown, item_type, any_value=any_value)
            dropdown.set_selected(0)

        self.log.debug("Assign to Project")
        box = self.factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
        dropdown = self.factory.create_dropdown_generic(Project)
        dropdown.connect("notify::selected-item", selected_item)
        self.actions.dropdown_populate(dropdown, Project, any_value=False)
        btnManage = self.factory.create_button('miaz-res-manage', '')
        btnManage.connect('clicked', self.on_resource_manage, Configview['Project'](self.app))
        label = self.factory.create_label('Assign the following documents to a project')
        frame = Gtk.Frame()
        cv = MiAZColumnViewMassProject(self.app)
        cv.get_style_context().add_class(class_name='monospace')
        cv.set_hexpand(True)
        cv.set_vexpand(True)
        citems = []
        for item in self.selected_items:
            citems.append(File(id=item.id, title=os.path.basename(item.id)))
        cv.update(citems)
        frame.set_child(cv)
        hbox = self.factory.create_box_horizontal(hexpand=False, vexpand=False)
        hbox.append(label)
        hbox.append(dropdown)
        hbox.append(btnManage)
        box.append(hbox)
        box.append(frame)
        dialog = self.factory.create_dialog_question(self.app.win, 'Assign to a project', box, width=1024, height=600)
        dialog.connect('response', self._on_mass_action_project_response, dropdown)
        dialog.show()

    def _on_mass_action_delete_dialog(self, *args):
        self.log.debug("Mass deletion")
        box = self.factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
        label = self.factory.create_label('Delete the following documents')
        frame = Gtk.Frame()
        cv = MiAZColumnViewMassDelete(self.app)
        cv.get_style_context().add_class(class_name='monospace')
        cv.set_hexpand(True)
        cv.set_vexpand(True)
        citems = []
        for item in self.selected_items:
            citems.append(File(id=item.id, title=os.path.basename(item.id)))
        cv.update(citems)
        frame.set_child(cv)
        box.append(label)
        box.append(frame)
        dialog = self.factory.create_dialog_question(self.app.win, 'Mass deletion', box, width=1024, height=600)
        dialog.connect('response', self._on_mass_action_delete_response)
        dialog.show()

    def _on_mass_action_delete_response(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            for item in self.selected_items:
                self.util.filename_delete(item.id)
        dialog.destroy()

    def _on_mass_action_project_response(self, dialog, response, dropdown):
        if response == Gtk.ResponseType.ACCEPT:
            self.projects = self.backend.projects
            pid = dropdown.get_selected_item().id
            docs = []
            for item in self.selected_items:
                docs.append(item.id)
            self.projects.add_batch(pid, docs)
        dialog.destroy()
