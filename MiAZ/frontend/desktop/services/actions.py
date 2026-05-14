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
        if any_value:
            model.append(item_type(id='Any', title=_('Any') + ' ' + i_title.lower()))
        if none_value:
            model.append(item_type(id='None', title=_('None') + ' ' + i_title.lower()))

        for key in items:
            accepted = True
            if len(only_include) > 0 and key not in only_include:
                accepted = False
            if len(only_exclude) > 0 and key in only_exclude:
                accepted = False

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

    def import_config(self, button, item_type):
        # FIXME: Implement import config
        srvdlg = self.app.get_service('dialogs')
        window = button.get_root()
        title = _("Action not implemented yet")
        body = _("Import the configuration hasn't been implemented yet")
        srvdlg.show_error(title=title, body=body, parent=window)

    def export_config(self, button, item_type):
        # FIXME: Implement export config
        srvdlg = self.app.get_service('dialogs')
        window = button.get_root()
        title = _("Action not implemented yet")
        body = ("Export the configuration hasn't been implemented yet")
        srvdlg.show_error(title=title, body=body, parent=window)

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
        self.app.emit("application-finished")
        self.app.quit()

    def stop_if_no_items(self, widget: Gtk.Widget = None):
        workspace = self.app.get_widget('workspace')
        stop = False
        items = workspace.get_selected_items()
        if len(items) == 0:
            srvdlg = self.app.get_service('dialogs')
            title = _('Action ignored. You must select at least one document')
            srvdlg.show_toast(message=title)
            stop = True
        return stop

    def application_restart(self, *args):
        ENV = self.app.get_env()
        python = sys.executable
        script = ENV['APP']['RUNTIME']['EXEC']
        self.app.emit('application-finished')
        self.log.info(f"Application restart: {python} {script} {sys.argv[1:]}")
        os.execv(python, [python, script] + sys.argv[1:])
