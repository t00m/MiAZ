#!/usr/bin/python3
# File: actions.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: App actions

import os
import glob
import pathlib
import zipfile
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import File, Group, Country, Purpose, SentBy, SentTo, Date, Repository
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries, MiAZGroups, MiAZPurposes, MiAZPeopleSentBy, MiAZPeopleSentTo, MiAZProjects
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassDelete
from MiAZ.frontend.desktop.widgets.settings import MiAZAppSettings
from MiAZ.frontend.desktop.widgets.settings import MiAZRepoSettings
from MiAZ.frontend.desktop.services.help import MiAZHelp

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
        super().__init__()
        self.log = MiAZLog('MiAZ.Actions')
        self.app = app

    def document_display(self, doc):
        srvutl = self.app.get_service('util')
        srvrepo = self.app.get_service('repo')
        self.log.debug(f"Displaying {doc}")
        filepath = os.path.join(srvrepo.docs, doc)
        srvutl.filename_display(filepath)

    def document_delete(self, items):
        factory = self.app.get_service('factory')
        srvutl = self.app.get_service('util')
        def dialog_response(dialog, response, items):
            if response == Gtk.ResponseType.ACCEPT:
                for item in items:
                    srvutl.filename_delete(item.id)
            dialog.destroy()

        self.log.debug("Mass deletion")
        frame = Gtk.Frame()
        box, view = factory.create_view(MiAZColumnViewMassDelete, _('Mass deletion'))
        citems = []
        for item in items:
            citems.append(File(id=item.id, title=os.path.basename(item.id)))
        view.update(citems)
        frame.set_child(view)
        box.append(frame)
        window = self.app.get_widget('window')
        dialog = factory.create_dialog_question(window, _('Mass deletion'), box, width=1024, height=600)
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
            model.append(item_type(id='Any', title=_(f'Any {i_title.lower()}')))
        if none_value:
            model.append(item_type(id='None', title=_(f'No {i_title.lower()}')))

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
                else:
                    title = f"{key} - {title}"
                model.append(item_type(id=key, title=title))

        if len(model) == 0:
            if item_type != Repository:
                model.append(item_type(id='None', title=_('No data')))
            else:
                model.append(item_type(id='None', title=_('No repositories found')))

    def import_config(self, button, item_type):
        factory = self.app.get_service('factory')
        i_title = item_type.__title__
        i_title_plural = item_type.__title_plural__
        file_available = f'{i_title_plural.lower()}-available.json'
        file_used = f'{i_title_plural.lower()}-used.json'

        def filechooser_response(dialog, response, data):
            if response == Gtk.ResponseType.ACCEPT:
                srvutl = self.app.get_service('util')
                content_area = dialog.get_content_area()
                box = content_area.get_first_child()
                filechooser = box.get_first_child()
                gfile = filechooser.get_file()
                if gfile is not None:
                    filepath = gfile.get_path()
                    files = srvutl.zip_list(filepath)
                    available_exists = file_available in files
                    self.log.debug(f"{file_available} exists? {available_exists}")
                    used_exists = file_used in files
                    self.log.debug(f"{file_used} exists? {used_exists}")
                    if available_exists and used_exists:
                        ENV = self.app.get_env()
                        srvutl.unzip(filepath, ENV['LPATH']['TMP'])
                        target_a = os.path.join(ENV['LPATH']['TMP'], file_available)
                        target_u = os.path.join(ENV['LPATH']['TMP'], file_used)
                        available = srvutl.json_load(target_a)
                        used = srvutl.json_load(target_u)
                        config = self.app.get_config_dict()
                        config_item = config[i_title]
                        config_item.add_used_batch(used.items())
                        config_item.add_available_batch(available.items())
                        self.show_repository_settings()
                        self.log.info(f"{i_title_plural} imported successfully")
                    else:
                        self.log.error(f"This is not a config file for {i_title_plural.lower()}")
            dialog.destroy()

        window = self.app.get_widget('window')
        filechooser = factory.create_filechooser(
                    parent=window,
                    title=_(f'Import a configuration file for {i_title_plural.lower()}'),
                    target = 'FILE',
                    callback = filechooser_response,
                    data = None)
        config_filter = Gtk.FileFilter()
        config_filter.add_pattern('*.zip')
        filechooser_widget = filechooser.get_filechooser_widget()
        filechooser_widget.set_filter(config_filter)
        filechooser.show()

    def export_config(self, button, item_type):
        factory = self.app.get_service('factory')
        # ~ i_title = item_type.__title__
        i_title_plural = item_type.__title_plural__
        # ~ file_available = '%s-available.json' % i_title_plural.lower()
        # ~ file_used = '%s-used.json' % i_title_plural.lower()
        name_available = item_type.__config_name_available__
        name_used = item_type.__config_name_used__

        def filechooser_response(dialog, response, data):
            srvutl = self.app.get_service('util')
            repository = self.app.get_service('repo')
            if response == Gtk.ResponseType.ACCEPT:
                content_area = dialog.get_content_area()
                box = content_area.get_first_child()
                filechooser = box.get_first_child()
                gfile = filechooser.get_file()
                if gfile is not None:
                    target_directory = gfile.get_path()
                    source_directory = pathlib.Path(os.path.join(repository.docs, '.conf'))
                    config_name_available = f"{name_available}-available.json"
                    config_name_used = f"{name_used}-used.json"
                    filenames = []
                    config_file_available = pathlib.Path(os.path.join(repository.docs, '.conf', config_name_available))
                    config_file_used = pathlib.Path(os.path.join(repository.docs, '.conf', config_name_used))
                    filenames.append(config_file_available)
                    filenames.append(config_file_used)
                    target_filename = f"miaz-{i_title_plural.lower()}-config-{srvutl.timestamp()}.zip"
                    target_filepath = os.path.join(target_directory, target_filename)
                    with zipfile.ZipFile(target_filepath, mode="w") as zip_archive:
                        for file_path in filenames:
                            zip_archive.write(
                                file_path,
                                arcname=file_path.relative_to(source_directory)
                            )
                    self.log.info(f"{i_title_plural} exported successfully to {target_filepath}")
                    self.show_repository_settings()
            dialog.destroy()

        window = self.app.get_widget('window')
        filechooser = factory.create_filechooser(
                    parent=window,
                    title=_(f'Export the configuration for {i_title_plural.lower()}'),
                    target = 'FOLDER',
                    callback = filechooser_response,
                    data = None)
        filechooser.show()

    def import_file(self, *args):
        factory = self.app.get_service('factory')
        srvutl = self.app.get_service('util')
        srvrepo = self.app.get_service('repo')
        def filechooser_response(dialog, response, data):
            if response == Gtk.ResponseType.ACCEPT:
                content_area = dialog.get_content_area()
                box = content_area.get_first_child()
                filechooser = box.get_first_child()
                gfile = filechooser.get_file()
                if gfile is not None:
                    source = gfile.get_path()
                    btarget = srvutl.filename_normalize(source)
                    target = os.path.join(srvrepo.docs, btarget)
                    srvutl.filename_import(source, target)
            dialog.destroy()

        window = self.app.get_widget('window')
        filechooser = factory.create_filechooser(
                    parent=window,
                    title=_('Import a single file'),
                    target = 'FILE',
                    callback = filechooser_response,
                    data = None
                    )
        filechooser.show()

    def manage_resource(self, widget: Gtk.Widget, selector: Gtk.Widget):
        factory = self.app.get_service('factory')
        box = factory.create_box_vertical(spacing=0, vexpand=True, hexpand=True)
        box.append(selector)
        config_for = selector.get_config_for()
        selector.set_vexpand(True)
        selector.update_views()
        window = self.app.get_widget('window')
        dialog = factory.create_dialog(window, _(f'Manage {config_for}'), box, 800, 600)
        dialog.show()

    def show_app_settings(self, *args):
        window = self.app.get_widget('window')
        settings = self.app.get_widget('settings-app')
        if settings is None:
            settings = self.app.add_widget('settings-app', MiAZAppSettings(self.app))
        settings.set_transient_for(window)
        settings.set_modal(True)
        settings.present()

    def show_repository_settings(self, *args):
        window_main = self.app.get_widget('window')
        window_settings = self.app.get_widget('settings-repo')
        if window_settings is None:
            window_settings = self.app.add_widget('settings-repo', MiAZRepoSettings(self.app))
        window_settings.set_transient_for(window_main)
        window_settings.set_modal(True)
        window_settings.update()
        window_settings.present()

    def show_app_about(self, *args):
        window = self.app.get_widget('window')
        ENV = self.app.get_env()
        about = Gtk.AboutDialog()
        about.set_transient_for=window
        about.set_modal(True)
        about.set_logo_icon_name(ENV['APP']['ID'])
        about.set_program_name(ENV['APP']['name'])
        about.set_version(ENV['APP']['VERSION'])
        authors = [f"{ENV['APP']['author']} {ENV['APP']['author_website']}"]
        about.set_authors(authors)
        artists = ['Flags borrowed from FlagKit project https://github.com/madebybowtie/FlagKit']
        artists.append('Icons borrowed from GNOME contributors https://www.gnome.org')
        about.set_artists(artists)
        about.set_license_type(Gtk.License.GPL_3_0_ONLY)
        about.set_copyright(f"© 2024 {ENV['APP']['author']}")
        about.set_website('https://github.com/t00m/MiAZ')
        about.set_website_label('Github MiAZ repository')
        about.set_comments(ENV['APP']['description'])
        about.present()

    def show_app_help(self, *args):
        shwin = self.app.get_widget('shortcutswindow')
        if shwin is None:
            shwin = Gtk.ShortcutsWindow()
            shwin.set_child(MiAZHelp(self.app))
            self.app.add_widget('shortcutswindow', shwin)
        shwin.present()

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
