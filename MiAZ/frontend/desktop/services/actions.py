#!/usr/bin/python3
# File: actions.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: App actions

import os
import sys
import pathlib
import zipfile
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Adw
from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import Group, Country, Purpose, SentBy, SentTo, Date, Repository
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries, MiAZGroups, MiAZPurposes, MiAZPeopleSentBy, MiAZPeopleSentTo
from MiAZ.frontend.desktop.widgets.configview import MiAZRepositories
from MiAZ.frontend.desktop.widgets.settings import MiAZAppSettings
from MiAZ.frontend.desktop.widgets.settings import MiAZRepoSettings

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
Configview['Date'] = Gtk.Calendar

class MiAZActions(GObject.GObject):
    def __init__(self, app):
        super().__init__()
        self.log = MiAZLog('MiAZ.Actions')
        self.app = app
        self.factory = self.app.get_service('factory')
        self.util = self.app.get_service('util')
        self.srvdlg = self.app.get_service('dialogs')
        GObject.signal_new('settings-loaded',
                            MiAZActions,
                            GObject.SignalFlags.RUN_LAST,
                            GObject.TYPE_PYOBJECT, (GObject.TYPE_PYOBJECT,))

    def document_display(self, doc):
        self.log.debug(f"Displaying {doc}")
        repository = self.app.get_service('repo')
        filepath = os.path.join(repository.docs, doc)
        self.util.filename_display(filepath)

    def dropdown_populate(self, config, dropdown, item_type, any_value=True, none_value=False, only_include: list = [], only_exclude: list = []):
        # FIXME: THIS METHOD DIDN'T TAKE INTO ACCOUNT CUSTOM MODELS
        #        IT HAS BEEN MODIFIED TO DETECT WHEN A MODEL IS STANDARD
        #        OR CUSTOM.
        # INFO: This method can be called as a reaction to the signal 'used-updated' or directly.
        # When reacting to a signal, config parameter is set in first place automatically.
        # When the method is called directly, config parameter must be passed.
        # In any case, config parameter is not used. Config is got from item_type
        i_type = item_type.__gtype_name__
        config_standard = self.app.get_config(i_type)
        if config_standard is not None:
            config = config_standard
        items = config.load(config.used)
        i_title = _(item_type.__title__)

        model_filter = dropdown.get_model()
        model_sort = model_filter.get_model()
        model = model_sort.get_model()
        model.remove_all()

        model.remove_all()
        if any_value:
            model.append(item_type(id='Any', title=_('Any'))) # {i_title.lower()}')))
        if none_value:
            model.append(item_type(id='None', title=_('None'))) # {i_title.lower()}')))

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
                    # ~ title = f"{key} - {title}"
                    title = f"{title}"
                model.append(item_type(id=key, title=title))

        if len(model) == 0:
            if item_type != Repository:
                model.append(item_type(id='None', title=_('No data')))
            else:
                model.append(item_type(id='None', title=_('No repositories found')))

    def import_config(self, button, item_type):
        # FIXME: Implement import config
        srvdlg = self.app.get_service('dialogs')
        window = button.get_root()
        title = _("Action not implemented yet")
        body = _("Import the configuration hasn't been implemented yet")
        srvdlg.show_error(title=title, body=body, parent=window)
        return

        factory = self.app.get_service('factory')
        i_title = item_type.__title__
        i_title_plural = item_type.__title_plural__
        file_available = f'{i_title_plural.lower()}-available.json'
        file_used = f'{i_title_plural.lower()}-used.json'

        def filechooser_response(dialog, response, data):
            if response == 'apply':
                srvutl = self.app.get_service('util')
                content_area = dialog.get_content_area()
                box = content_area.get_first_child()
                filechooser = box.get_first_child()
                gfile = filechooser.get_file()
                if gfile is not None:
                    filepath = gfile.get_path()
                    files = self.util.zip_list(filepath)
                    available_exists = file_available in files
                    self.log.debug(f"{file_available} exists? {available_exists}")
                    used_exists = file_used in files
                    self.log.debug(f"{file_used} exists? {used_exists}")
                    if available_exists and used_exists:
                        ENV = self.app.get_env()
                        self.util.unzip(filepath, ENV['LPATH']['TMP'])
                        target_a = os.path.join(ENV['LPATH']['TMP'], file_available)
                        target_u = os.path.join(ENV['LPATH']['TMP'], file_used)
                        available = self.util.json_load(target_a)
                        used = self.util.json_load(target_u)
                        config = self.app.get_config_dict()
                        config_item = config[i_title]
                        config_item.add_used_batch(used.items())
                        config_item.add_available_batch(available.items())
                        self.show_repository_settings()
                        self.log.info(f"{i_title_plural} imported successfully")
                    else:
                        self.log.error(f"This is not a config file for {i_title_plural.lower()}")

        window = self.app.get_widget('window')
        # FIXME: use the new filechooser
        filechooser = factory.create_filechooser(
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
        # FIXME: Implement export config
        srvdlg = self.app.get_service('dialogs')
        window = button.get_root()
        title = _("Action not implemented yet")
        body = ("Export the configuration hasn't been implemented yet")
        srvdlg.show_error(title=title, body=body, parent=window)
        return

        # ~ i_title = item_type.__title__
        # ~ file_available = '%s-available.json' % i_title_plural.lower()
        # ~ file_used = '%s-used.json' % i_title_plural.lower()
        factory = self.app.get_service('factory')
        i_title_plural = item_type.__title_plural__
        name_available = item_type.__config_name_available__
        name_used = item_type.__config_name_used__

        def filechooser_response(dialog, response, data):
            srvutl = self.app.get_service('util')
            repository = self.app.get_service('repo')
            if response == 'apply':
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
                    target_filename = f"miaz-{i_title_plural.lower()}-config-{self.util.timestamp()}.zip"
                    target_filepath = os.path.join(target_directory, target_filename)
                    with zipfile.ZipFile(target_filepath, mode="w") as zip_archive:
                        for file_path in filenames:
                            zip_archive.write(
                                file_path,
                                arcname=file_path.relative_to(source_directory)
                            )
                    self.log.info(f"{i_title_plural} exported successfully to {target_filepath}")
                    self.show_repository_settings()

        window = self.app.get_widget('window')
        # FIXME: use the new filechooser
        filechooser = factory.create_filechooser(
                    title=_(f'Export the configuration for {i_title_plural.lower()}'),
                    target = 'FOLDER',
                    callback = filechooser_response,
                    data = None)
        filechooser.show()

    def manage_resource(self, widget: Gtk.Widget, selector: Gtk.Widget):
        factory = self.app.get_service('factory')
        srvdlg = self.app.get_service('dialogs')
        parent = widget.get_root() # wonderful

        box = factory.create_box_vertical(spacing=0, vexpand=True, hexpand=True)
        box.append(selector)
        config_for = selector.get_config_for()
        selector.set_vexpand(True)
        selector.update_views()
        title = _(f'Manage {config_for}')
        dialog = srvdlg.show_action(title=title, widget=box, width=800, height=600)
        dialog.present(parent)

    def show_app_settings(self, *args):
        window = self.app.get_widget('window')
        dialog_app_settings = MiAZAppSettings(self.app)
        dialog_app_settings.present(window)
        self.app.add_widget('window-settings', dialog_app_settings)
        self.emit('settings-loaded', dialog_app_settings)

    def show_repository_settings(self, *args):
        try:
            # Continue if a default repository exists
            appconf = self.app.get_config('App')
            repo_id = appconf.get('current').replace('_', ' ')
            window_main = self.app.get_widget('window')
            window_repoconfig = MiAZRepoSettings(self.app)
            window_repoconfig.set_transient_for(window_main)
            window_repoconfig.set_modal(True)
            window_repoconfig.update()
            window_repoconfig.present()
        except AttributeError:
            srvdlg = self.app.get_service('dialogs')
            parent = self.app.get_widget('window')
            title = _("Repository management")
            body = _("There aren't repositories configured.\nPlease, create one.")
            srvdlg.show_error(title=title, body=body, parent=parent)

    def show_repository_manager(self, *args):
        widget = self.factory.create_box_vertical(hexpand=True, vexpand=True)
        configview = MiAZRepositories(self.app)
        configview.set_hexpand(True)
        configview.set_vexpand(True)
        configview.update_views()
        widget.append(configview)
        window = self.app.get_widget('window')
        title = _('Repository management')
        body = ""
        srvdlg = self.app.get_service('dialogs')
        dialog = srvdlg.show_noop(title=title, body=body, widget=widget, width=800, height=600)
        dialog.present(window)

    def show_app_about(self, *args):
        # FIXME: App icon not displayed in local installation
        window = self.app.get_widget('window')
        ENV = self.app.get_env()
        about = Adw.AboutDialog()
        about.set_application_icon('io.github.t00m.MiAZ')
        about.set_application_name(ENV['APP']['name'])
        about.set_version(ENV['APP']['VERSION'])
        author = f"{ENV['APP']['author']}"
        about.set_developer_name(author)
        artists = [_('Flags borrowed from FlagKit project https://github.com/madebybowtie/FlagKit')]
        artists.append(_('Some icons borrowed from GNOME contributors https://www.gnome.org'))
        artists.append(_("MiAZ app icon based on Collection Business Duotone Icons with license 'CC Attribution License' by 'cataicon' https://www.svgrepo.com/svg/391994/binder-business-finance-management-marketing-office"))
        about.set_artists(artists)
        about.set_license_type(Gtk.License.GPL_3_0_ONLY)
        about.set_copyright(f"© 2019-2025 {ENV['APP']['author']}")
        about.set_website('https://github.com/t00m/MiAZ')
        about.set_comments(ENV['APP']['description'])
        # ~ README = open(ENV['FILE']['README'], 'r').read()
        # ~ about.set_comments(README)
        about.present(window)

    def show_app_help(self, *args):
        pass
        # ~ shwin = self.app.get_widget('shortcutswindow')
        # ~ if shwin is None:
            # ~ shwin = MiAZShortcutsWindow()
            # ~ self.app.add_widget('shortcutswindow', shwin)
        # ~ shwin.present()

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

    def exit_app(self, *args):
        self.log.debug('Closing MiAZ')
        webserver = self.app.get_service('webserver')
        webserver.stop()
        self.app.emit("application-finished")
        self.app.quit()

    def stop_if_no_items(self, widget: Gtk.Widget = None):
        workspace = self.app.get_widget('workspace')
        stop = False
        items = workspace.get_selected_items()
        if len(items) == 0:
            srvdlg = self.app.get_service('dialogs')
            if widget is None:
                widget = self.app.get_widget('workspace')
            parent = widget.get_root()
            body = _('You must select at least one document')
            title = _('Action ignored')
            srvdlg.show_error(title=title, body=body, parent=parent)
            stop = True
        return stop

    def application_restart(self, *args):
        ENV = self.app.get_env()
        python = sys.executable
        script = ENV['APP']['RUNTIME']['EXEC']
        self.app.emit('application-finished')
        self.log.info("Application restart: {python} {script} {sys.argv[1:]}")
        os.execv(python, [python, script] + sys.argv[1:])
