#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: actions.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: App actions
"""

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

class MiAZActions(GObject.GObject):
    def __init__(self, app):
        self.log = get_logger('MiAZActions')
        self.app = app
        self.backend = self.app.get_backend()
        self.util = self.backend.util

    def document_display(self, doc):
        self.log.debug("Displaying %s", doc)
        self.util.filename_display(doc)

    def document_open_location(self, item):
        self.log.debug("Open file location for %s", item.id)
        self.util.filename_open_location(item.id)

    def document_delete(self, items):
        def dialog_response(dialog, response, items):
            if response == Gtk.ResponseType.ACCEPT:
                for item in items:
                    self.util.filename_delete(item.id)
            dialog.destroy()

        self.log.debug("Mass deletion")
        self.factory = self.app.get_factory()
        self.config = self.backend.conf
        frame = Gtk.Frame()
        box, view = self.factory.create_view(MiAZColumnViewMassDelete, "Mass deletion")
        # ~ box = self.factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
        # ~ label = self.factory.create_label('Delete the following documents')
        # ~ frame = Gtk.Frame()
        # ~ cv = MiAZColumnViewMassDelete(self.app)
        # ~ cv.get_style_context().add_class(class_name='monospace')
        # ~ cv.set_hexpand(True)
        # ~ cv.set_vexpand(True)
        citems = []
        for item in items:
            citems.append(File(id=item.id, title=os.path.basename(item.id)))
        view.update(citems)
        frame.set_child(view)
        # ~ box.append(label)
        box.append(frame)
        dialog = self.factory.create_dialog_question(self.app.win, 'Mass deletion', box, width=1024, height=600)
        dialog.connect('response', dialog_response, items)
        dialog.show()

    def document_rename_single(self, doc):
        self.log.debug("Rename %s", doc)
        rename = self.app.get_rename_widget()
        rename.set_data(doc)
        self.app.show_stack_page_by_name('rename')

    def document_rename(self, items):

        def update_columnview(dropdown, gparamobj, columnview, dropdowns, items):
            citems = []
            for item in items:
                try:
                    source = item.id
                    name, ext = self.util.filename_details(source)
                    tmpfile = name.split('-')
                    for item_type in dropdowns:
                        n = Field[item_type]
                        value = dropdowns[item_type].get_selected_item().id
                        if value != 'None':
                            tmpfile[n] = value
                    filename = "%s.%s" % ('-'.join(tmpfile), ext)
                    target = os.path.join(os.path.dirname(source), filename)
                    txtId = "<small>%s</small>" % os.path.basename(source)
                    txtTitle = "<small>%s</small>" % os.path.basename(target)
                    citems.append(File(id=txtId, title=txtTitle))
                except Exception as error:
                    # FIXME: AtributeError: 'NoneType' object has no attribute 'id'
                    # It happens when managing resources from inside the dialog
                    # Non critical
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

        def dialog_response(dialog, response, dropdown, dropdowns, items):
            if response == Gtk.ResponseType.ACCEPT:
                for item in items:
                    source = item.id
                    name, ext = self.util.filename_details(source)
                    tmpfile = name.split('-')
                    for item_type in dropdowns:
                        n = Field[item_type]
                        value = dropdowns[item_type].get_selected_item().id
                        if value != 'None':
                            tmpfile[n] = value
                        filename = "%s.%s" % ('-'.join(tmpfile), ext)
                    target = os.path.join(os.path.dirname(source), filename)
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

        box = self.factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
        frame = Gtk.Frame()
        cv = MiAZColumnViewMassRename(self.app)
        cv.get_style_context().add_class(class_name='monospace')
        cv.set_hexpand(True)
        cv.set_vexpand(True)
        frame.set_child(cv)
        dropdowns = {}
        for item_type in [Country, Group, SentBy, Purpose, SentTo]:
            i_type = item_type.__gtype_name__
            i_title = item_type.__title__
            label = self.factory.create_label('Rename %d files by setting the field <b>%s</b> to:\n' % (len(items), i_title))
            label.set_yalign(0.5)
            dropdown = self.factory.create_dropdown_generic(item_type=item_type)
            dropdowns[item_type] = dropdown
            btnManage = self.factory.create_button('miaz-res-manage', '')
            btnManage.connect('clicked', self.manage_resource, Configview[i_type](self.app))
            self.dropdown_populate(self.config[i_type], dropdown, item_type, any_value=False, none_value=True)
            dropdown.connect("notify::selected-item", update_columnview, cv, dropdowns, items)
            self.config[i_type].connect('used-updated', self.dropdown_populate, dropdown, item_type, False)
            hbox = self.factory.create_box_horizontal(hexpand=False)
            hbox.append(label)
            hbox.append(dropdown)
            hbox.append(btnManage)
            box.append(hbox)
        box.append(frame)
        dialog = self.factory.create_dialog_question(self.app.win, 'Mass renaming', box, width=1024, height=600)
        dialog.connect('response', dialog_response, dropdown, dropdowns, items)
        dialog.show()

        # ~ else:
            # ~ box = self.factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
            # ~ hbox = self.factory.create_box_horizontal()
            # ~ label = Gtk.Label()
            # ~ calendar = Gtk.Calendar()
            # ~ btnDate = self.factory.create_button_popover(icon_name='miaz-res-date', widgets=[calendar])
            # ~ hbox.append(btnDate)
            # ~ hbox.append(label)
            # ~ frame = Gtk.Frame()
            # ~ cv = MiAZColumnViewMassRename(self.app)
            # ~ cv.get_style_context().add_class(class_name='monospace')
            # ~ cv.set_hexpand(True)
            # ~ cv.set_vexpand(True)
            # ~ frame.set_child(cv)
            # ~ box.append(hbox)
            # ~ box.append(frame)
            # ~ sdate = datetime.strftime(datetime.now(), '%Y%m%d')
            # ~ iso8601 = "%sT00:00:00Z" % sdate
            # ~ calendar.connect('day-selected', calendar_day_selected, label, cv, items)
            # ~ calendar.select_day(GLib.DateTime.new_from_iso8601(iso8601))
            # ~ calendar.emit('day-selected')
            # ~ dialog = self.factory.create_dialog_question(self.app.win, 'Mass renaming', box, width=640, height=480)
            # ~ dialog.connect('response', dialog_response_date, calendar, items)
            # ~ dialog.show()

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
            box = self.factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
            label = self.factory.create_label('Rename %d files by setting the field <b>%s</b> to:\n' % (len(items), i_title))
            dropdown = self.factory.create_dropdown_generic(item_type)
            btnManage = self.factory.create_button('miaz-res-manage', '')
            btnManage.connect('clicked', self.manage_resource, Configview[i_type](self.app))
            frame = Gtk.Frame()
            cv = MiAZColumnViewMassRename(self.app)
            cv.get_style_context().add_class(class_name='monospace')
            cv.set_hexpand(True)
            cv.set_vexpand(True)
            dropdown.connect("notify::selected-item", update_columnview, cv, item_type, items)
            self.config[i_type].connect('used-updated', self.dropdown_populate, dropdown, item_type, False)
            self.dropdown_populate(self.config[i_type], dropdown, item_type, any_value=False)
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

    def dropdown_populate(self, config, dropdown, item_type, any_value=True, none_value=False, only_include: list = [], only_exclude: list = []):
        # FIXME? This method can be called as a reaction to the signal
        # 'used-updated' or directly. When reacting to a signal, config
        # parameter is set in first place. When the method is called
        # directly, config parameter must be passed.
        # In any case, config parameter is not used. Config is got from
        # item_type
        # ~ model = dropdown.get_model()
        i_type = item_type.__gtype_name__
        config = self.app.get_config(i_type)
        items = config.load(config.used)
        i_title = item_type.__title__

        model_filter = dropdown.get_model()
        model_sort = model_filter.get_model()
        model = model_sort.get_model()
        model.remove_all()

        model.remove_all()
        if any_value:
            model.append(item_type(id='Any', title='Any %s' % i_title.lower()))
        if none_value:
            model.append(item_type(id='None', title='No %s' % i_title.lower()))

        for key in items:
            accepted = True
            if len(only_include) > 0 and key in only_include:
                accepted = True
            else:
                accepted = False

            if len(only_exclude) > 0 and key in only_exclude:
                accepted = False
            else:
                accepted = True

            if accepted:
                title = items[key]
                if len(title) == 0:
                    title = key
                model.append(item_type(id=key, title=title))

    def import_directory(self, *args):
        def filechooser_response(dialog, response, data):
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
                        self.util.filename_import(source, target)
            dialog.destroy()

        self.factory = self.app.get_factory()
        filechooser = self.factory.create_filechooser(
                    parent=self.app.win,
                    title='Import a directory',
                    target = 'FOLDER',
                    callback = filechooser_response,
                    data = None
                    )
        contents = filechooser.get_content_area()
        box = contents.get_first_child()
        toggle = self.factory.create_button_check(title='Walk recursively', callback=None)
        box.append(toggle)
        filechooser.show()

    def import_file(self, *args):
        def filechooser_response(dialog, response, data):
            config = self.backend.repo_config()
            target_dir = config['dir_docs']
            if response == Gtk.ResponseType.ACCEPT:
                content_area = dialog.get_content_area()
                box = content_area.get_first_child()
                filechooser = box.get_first_child()
                gfile = filechooser.get_file()
                if gfile is not None:
                    source = gfile.get_path()
                    target = self.util.filename_normalize(source)
                    self.util.filename_import(source, target)
            dialog.destroy()

        self.factory = self.app.get_factory()
        filechooser = self.factory.create_filechooser(
                    parent=self.app.win,
                    title='Import a single file',
                    target = 'FILE',
                    callback = filechooser_response,
                    data = None
                    )
        filechooser.show()

    def manage_resource(self, widget: Gtk.Widget, selector: Gtk.Widget):
        factory = self.app.get_factory()
        box = factory.create_box_vertical(spacing=0, vexpand=True, hexpand=True)
        box.append(selector)
        config_for = selector.get_config_for()
        selector.set_vexpand(True)
        selector.update()
        dialog = factory.create_dialog(self.app.win, 'Manage %s' % config_for, box, 800, 600)
        dialog.show()


    def project_assign(self, item_type, items):
        def dialog_response(dialog, response, dropdown, items):
            if response == Gtk.ResponseType.ACCEPT:
                self.projects = self.backend.projects
                pid = dropdown.get_selected_item().id
                docs = []
                for item in items:
                    docs.append(os.path.basename(item.id))
                self.projects.add_batch(pid, docs)
                workspace = self.app.get_workspace()
                workspace.update()
            dialog.destroy()

        self.factory = self.app.get_factory()
        self.config = self.backend.conf
        i_type = item_type.__gtype_name__
        box = self.factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
        dropdown = self.factory.create_dropdown_generic(Project)
        self.config[i_type].connect('used-updated', self.dropdown_populate, dropdown, item_type, False, False)
        self.dropdown_populate(self.config[i_type], dropdown, Project, any_value=False)
        btnManage = self.factory.create_button('miaz-res-manage', '')
        btnManage.connect('clicked', self.manage_resource, Configview['Project'](self.app))
        label = self.factory.create_label('Assign the following documents to this project: ')
        frame = Gtk.Frame()
        cv = MiAZColumnViewMassProject(self.app)
        cv.get_style_context().add_class(class_name='monospace')
        cv.set_hexpand(True)
        cv.set_vexpand(True)
        citems = []
        for item in items:
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
        dialog.connect('response', dialog_response, dropdown, items)
        dialog.show()

    def project_withdraw(self, item_type, items):
        def dialog_response(dialog, response, dropdown, items):
            if response == Gtk.ResponseType.ACCEPT:
                self.projects = self.backend.projects
                pid = dropdown.get_selected_item().id
                docs = []
                for item in items:
                    docs.append(os.path.basename(item.id))
                self.projects.remove_batch(pid, docs)
                workspace = self.app.get_workspace()
                workspace.update()
            dialog.destroy()

        self.factory = self.app.get_factory()
        self.config = self.backend.conf
        i_type = item_type.__gtype_name__
        box = self.factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
        dropdown = self.factory.create_dropdown_generic(Project)
        self.config[i_type].connect('used-updated', self.dropdown_populate, dropdown, item_type, False, False)

        # Get projects
        projects = set()
        for item in items:
            for project in self.backend.projects.assigned_to(item.id):
                projects.add(project)

        self.dropdown_populate(self.config[i_type], dropdown, Project, any_value=False, only_include=list(projects))
        btnManage = self.factory.create_button('miaz-res-manage', '')
        btnManage.connect('clicked', self.manage_resource, Configview['Project'](self.app))
        label = self.factory.create_label('Withdraw the following documents from this project: ')
        frame = Gtk.Frame()
        cv = MiAZColumnViewMassProject(self.app)
        cv.get_style_context().add_class(class_name='monospace')
        cv.set_hexpand(True)
        cv.set_vexpand(True)
        citems = []
        for item in items:
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
        dialog.connect('response', dialog_response, dropdown, items)
        dialog.show()

    def document_export_to_directory(self, items):
        def get_pattern_paths(item):
            fields = self.util.get_fields(item.id)
            paths = {}
            paths['Y'] = '%04d' % datetime.strptime(fields[0], '%Y%m%d').year
            paths['m'] = "%02d" % datetime.strptime(fields[0], '%Y%m%d').month
            paths['d'] = "%02d" % datetime.strptime(fields[0], '%Y%m%d').day
            paths['C'] = fields[Field[Country]]
            paths['G'] = fields[Field[Group]]
            paths['P'] = fields[Field[Purpose]]
            paths['B'] = fields[Field[SentBy]]
            paths['T'] = fields[Field[SentTo]]
            return paths

        def filechooser_response(dialog, response, patterns):
            config = self.backend.repo_config()
            target_dir = config['dir_docs']
            if response == Gtk.ResponseType.ACCEPT:
                content_area = dialog.get_content_area()
                box = content_area.get_first_child()
                filechooser = box.get_first_child()
                hbox = box.get_last_child()
                toggle_pattern = hbox.get_first_child()
                gfile = filechooser.get_file()
                if gfile is not None:
                    dirpath = gfile.get_path()
                    if toggle_pattern.get_active():
                        entry = toggle_pattern.get_next_sibling()
                        keys = [key for key in entry.get_text()]
                        for item in items:
                            basename = os.path.basename(item.id)
                            self.log.debug(basename)
                            thispath = []
                            thispath.append(dirpath)
                            paths = get_pattern_paths(item)
                            for key in keys:
                                thispath.append(paths[key])
                            target = os.path.join(*thispath)
                            os.makedirs(target, exist_ok = True)
                            self.util.filename_export(item.id, target)
                    else:
                        for item in items:
                            target = os.path.join(dirpath, os.path.basename(item.id))
                            self.util.filename_export(item.id, target)
                    self.util.directory_open(dirpath)
            dialog.destroy()

        self.factory = self.app.get_factory()
        patterns = {
            'Y': 'Year',
            'm': 'Month',
            'd': 'Day',
            'C': 'Country',
            'G': 'Group',
            'P': 'Purpose',
            'B': 'Sent by',
            'T': 'Sent to',
        }
        filechooser = self.factory.create_filechooser(
                    parent=self.app.win,
                    title='Export selected items to this directory',
                    target = 'FOLDER',
                    callback = filechooser_response,
                    data = patterns
                    )

        # Export with pattern
        contents = filechooser.get_content_area()
        box = contents.get_first_child()
        hbox = self.factory.create_box_horizontal()
        chkPattern = self.factory.create_button_check(title='Export with pattern', callback=None)
        etyPattern = Gtk.Entry()
        etyPattern.set_text('CYmGP') #/{target}/{Country}/{Year}/{month}/{Group}/{Purpose}
        widgets = []
        for key in patterns:
            label = Gtk.Label()
            label.set_markup('<b>%s</b> = %s' % (key, patterns[key]))
            label.set_xalign(0.0)
            widgets.append(label)
        btpPattern = self.factory.create_button_popover(icon_name='miaz-info', widgets=widgets)
        hbox.append(chkPattern)
        hbox.append(etyPattern)
        hbox.append(btpPattern)
        box.append(hbox)
        filechooser.show()

    def document_export_to_zip(self, items):
        self.log.debug("Not implemented yet")
        return
        def filechooser_response(dialog, response, patterns):
            config = self.backend.repo_config()
            target_dir = config['dir_docs']
            if response == Gtk.ResponseType.ACCEPT:
                content_area = dialog.get_content_area()
                box = content_area.get_first_child()
                filechooser = box.get_first_child()
                hbox = box.get_last_child()
                toggle_pattern = hbox.get_first_child()
                gfile = filechooser.get_file()
                if gfile is not None:
                    dirpath = gfile.get_path()
                    self.util.zip('miaz-export.zip', dirpath)
            dialog.destroy()

        self.factory = self.app.get_factory()
        filechooser = self.factory.create_filechooser(
                    parent=self.app.win,
                    title='Export selected documents to a ZIP file',
                    target = 'FOLDER',
                    callback = filechooser_response,
                    data = None
                    )

        # Export with pattern
        filechooser.show()
