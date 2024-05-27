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
import tempfile
from datetime import datetime
from gettext import gettext as _

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from MiAZ.backend.log import get_logger
from MiAZ.backend.models import MiAZItem, File, Group, Person, Country, Purpose, Concept, SentBy, SentTo, Date, Extension, Project, Repository
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
        self.log = get_logger('MiAZ.Actions')
        self.app = app
        self.backend = self.app.get_service('backend')
        self.util = self.app.get_service('util')
        self.factory = self.app.get_service('factory')
        self.repository = self.app.get_service('repo')

    def document_display(self, doc):
        self.log.debug("Displaying %s", doc)
        repo_dir = self.repository.get('dir_docs')
        filepath = os.path.join(repo_dir, doc)
        self.util.filename_display(filepath)

    # ~ def document_open_location(self, item):
        # ~ self.log.debug("Open file location for %s", item.id)
        # ~ self.util.filename_open_location(item.id)

    def document_delete(self, items):
        def dialog_response(dialog, response, items):
            if response == Gtk.ResponseType.ACCEPT:
                for item in items:
                    self.util.filename_delete(item.id)
            dialog.destroy()

        self.log.debug("Mass deletion")
        self.config = self.backend.get_config()
        frame = Gtk.Frame()
        box, view = self.factory.create_view(MiAZColumnViewMassDelete, _('Mass deletion'))
        citems = []
        for item in items:
            citems.append(File(id=item.id, title=os.path.basename(item.id)))
        view.update(citems)
        frame.set_child(view)
        box.append(frame)
        dialog = self.factory.create_dialog_question(self.app.win, _('Mass deletion'), box, width=1024, height=600)
        dialog.connect('response', dialog_response, items)
        dialog.show()

    def dropdown_populate(self, config, dropdown, item_type, any_value=True, none_value=False, only_include: list = [], only_exclude: list = []):
        # INFO: This method can be called as a reaction to the signal
        # 'used-updated' or directly. When reacting to a signal, config
        # parameter is set in first place. When the method is called
        # directly, config parameter must be passed.
        # In any case, config parameter is not used. Config is got from
        # item_type
        i_type = item_type.__gtype_name__
        config = self.app.get_config(i_type)
        items = config.load(config.used)
        i_title = _(item_type.__title__)

        model_filter = dropdown.get_model()
        model_sort = model_filter.get_model()
        model = model_sort.get_model()
        model.remove_all()

        model.remove_all()
        if any_value:
            model.append(item_type(id='Any', title=_('Any %s') % i_title.lower()))
        if none_value:
            model.append(item_type(id='None', title=_('No %s') % i_title.lower()))

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
                if item_type == Repository:
                    title = key.replace('_', ' ')
                model.append(item_type(id=key, title=title))

        if len(model) == 0:
            if item_type != Repository:
                model.append(item_type(id='None', title=_('No data')))
            else:
                model.append(item_type(id='None', title=_('No repositories found')))

    def import_directory(self, *args):
        def filechooser_response(dialog, response, data):
            target_dir = self.repository.get('dir_docs')
            if response == Gtk.ResponseType.ACCEPT:
                content_area = dialog.get_content_area()
                box = content_area.get_first_child()
                filechooser = box.get_first_child()
                toggle = box.get_last_child()
                recursive = toggle.get_active()
                gfile = filechooser.get_file()
                repo_dir = self.repository.get('dir_docs')
                if gfile is not None:
                    dirpath = gfile.get_path()
                    self.log.debug("Walk directory %s recursively? %s", dirpath, recursive)
                    if recursive:
                        files = self.util.get_files_recursively(dirpath)
                    else:
                        files = glob.glob(os.path.join(dirpath, '*.*'))
                    for source in files:
                        btarget = self.util.filename_normalize(source)
                        target = os.path.join(repo_dir, btarget)
                        self.util.filename_import(source, target)
            dialog.destroy()

        filechooser = self.factory.create_filechooser(
                    parent=self.app.win,
                    title=_('Import a directory'),
                    target = 'FOLDER',
                    callback = filechooser_response,
                    data = None
                    )
        contents = filechooser.get_content_area()
        box = contents.get_first_child()
        toggle = self.factory.create_button_check(title=_('Walk recursively'), callback=None)
        box.append(toggle)
        filechooser.show()

    def import_config(self, *args):
        def filechooser_response(dialog, response, data):
            target_dir = self.repository.get('dir_docs')
            if response == Gtk.ResponseType.ACCEPT:
                content_area = dialog.get_content_area()
                box = content_area.get_first_child()
                filechooser = box.get_first_child()
                gfile = filechooser.get_file()
                if gfile is not None:
                    source = gfile.get_path()
                    self.log.debug(source)
            dialog.destroy()

        filechooser = self.factory.create_filechooser(
                    parent=self.app.win,
                    title=_('Import a configuration file'),
                    target = 'FILE',
                    callback = filechooser_response,
                    data = None
                    )
        filechooser.show()

    def import_file(self, *args):
        def filechooser_response(dialog, response, data):
            repo_dir = self.repository.get('dir_docs')
            if response == Gtk.ResponseType.ACCEPT:
                content_area = dialog.get_content_area()
                box = content_area.get_first_child()
                filechooser = box.get_first_child()
                gfile = filechooser.get_file()
                if gfile is not None:
                    source = gfile.get_path()
                    btarget = self.util.filename_normalize(source)
                    target = os.path.join(repo_dir, btarget)
                    self.util.filename_import(source, target)
            dialog.destroy()

        filechooser = self.factory.create_filechooser(
                    parent=self.app.win,
                    title=_('Import a single file'),
                    target = 'FILE',
                    callback = filechooser_response,
                    data = None
                    )
        filechooser.show()

    def manage_resource(self, widget: Gtk.Widget, selector: Gtk.Widget):
        box = self.factory.create_box_vertical(spacing=0, vexpand=True, hexpand=True)
        box.append(selector)
        config_for = selector.get_config_for()
        selector.set_vexpand(True)
        selector.update()
        dialog = self.factory.create_dialog(self.app.win, _('Manage %s') % config_for, box, 800, 600)
        dialog.show()
