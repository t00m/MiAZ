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

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import MiAZItem, File, Group, Person, Country, Purpose, Concept, SentBy, SentTo, Date, Extension, Project, Repository
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries, MiAZGroups, MiAZPeople, MiAZPurposes, MiAZPeopleSentBy, MiAZPeopleSentTo, MiAZProjects
from MiAZ.frontend.desktop.widgets.rename import MiAZRenameDialog
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewWorkspace
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassRename
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassDelete
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassProject
from MiAZ.frontend.desktop.widgets.settings import MiAZAppSettings

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
        self.log = MiAZLog('MiAZ.Actions')
        self.app = app
        self.util = self.app.get_service('util')
        self.factory = self.app.get_service('factory')
        self.repository = self.app.get_service('repo')

    def document_display(self, doc):
        self.log.debug("Displaying %s", doc)
        filepath = os.path.join(self.repository.docs, doc)
        self.util.filename_display(filepath)

    def document_delete(self, items):
        def dialog_response(dialog, response, items):
            if response == Gtk.ResponseType.ACCEPT:
                for item in items:
                    self.util.filename_delete(item.id)
            dialog.destroy()

        self.log.debug("Mass deletion")
        self.config = self.app.get_config_dict()
        frame = Gtk.Frame()
        box, view = self.factory.create_view(MiAZColumnViewMassDelete, _('Mass deletion'))
        citems = []
        for item in items:
            citems.append(File(id=item.id, title=os.path.basename(item.id)))
        view.update(citems)
        frame.set_child(view)
        box.append(frame)
        window = self.app.get_widget('window')
        dialog = self.factory.create_dialog_question(window, _('Mass deletion'), box, width=1024, height=600)
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
                        btarget = self.util.filename_normalize(source)
                        target = os.path.join(self.repository.docs, btarget)
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
            if response == Gtk.ResponseType.ACCEPT:
                content_area = dialog.get_content_area()
                box = content_area.get_first_child()
                filechooser = box.get_first_child()
                gfile = filechooser.get_file()
                if gfile is not None:
                    source = gfile.get_path()
                    btarget = self.util.filename_normalize(source)
                    target = os.path.join(self.repository.docs, btarget)
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
        window = self.app.get_widget('window')
        dialog = self.factory.create_dialog(window, _('Manage %s') % config_for, box, 800, 600)
        dialog.show()

    def show_app_settings(self, *args):
        window = self.app.get_widget('window')
        settings = self.app.get_widget('settings-app')
        if settings is None:
            settings = self.app.add_widget('settings-app', MiAZAppSettings(self.app))
        settings.set_transient_for(window)
        settings.set_modal(True)
        settings.present()

    def show_app_about(self, *args):
        window = self.app.get_widget('window')
        ENV = self.app.get_env()
        about = Gtk.AboutDialog()
        about.set_transient_for=window
        about.set_modal(True)
        about.set_logo_icon_name(ENV['APP']['ID'])
        about.set_program_name(ENV['APP']['name'])
        about.set_version(ENV['APP']['VERSION'])
        authors = ['%s %s' % (ENV['APP']['author'], ENV['APP']['author_website'])]
        about.set_authors(authors)
        artists = ['Flags borrowed from FlagKit project https://github.com/madebybowtie/FlagKit']
        artists.append('Icons borrowed from GNOME contributors https://www.gnome.org')
        about.set_artists(artists)
        about.set_license_type(Gtk.License.GPL_3_0_ONLY)
        about.set_copyright('© 2024 %s' % ENV['APP']['author'])
        about.set_website('https://github.com/t00m/MiAZ')
        about.set_website_label('Github MiAZ repository')
        about.set_comments(ENV['APP']['description'])
        about.present()

    def get_stack_page_by_name(self, name: str) -> Gtk.Stack:
        stack = self.app.get_widget('stack')
        widget = stack.get_child_by_name(name)
        return stack.get_page(widget)

    def get_stack_page_widget_by_name(self, name:str) -> Gtk.Widget:
        stack = self.app.get_widget('stack')
        return stack.get_child_by_name(name)

    def show_stack_page_by_name(self, name: str = 'workspace'):
        stack = self.app.get_widget('stack')
        stack.set_visible_child_name(name)

    def noop(self, *args):
        pass

    def toggle_workspace_filters(self, *args):
        btnShowFilters = self.app.get_widget('workspace-togglebutton-filters')
        active = btnShowFilters.get_active()
        btnShowFilters.set_active(not active)

    def exit_app(self, *args):
        self.log.debug('Closing MiAZ')
        self.app.emit("exit-application")
        self.app.quit()
