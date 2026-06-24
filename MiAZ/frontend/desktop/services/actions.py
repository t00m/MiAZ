#!/usr/bin/python3
# File: actions.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: App actions

import os
import sys
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Adw
from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import Group, Country, Purpose, SentBy, SentTo, Date, Repository, File
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries, MiAZGroups, MiAZPurposes, MiAZPeopleSentBy, MiAZPeopleSentTo
from MiAZ.frontend.desktop.widgets.configview import MiAZRepositories
from MiAZ.frontend.desktop.services.dialogs import MiAZWindowDialog
from MiAZ.frontend.desktop.widgets.rename import MiAZRenameDialog
from MiAZ.frontend.desktop.widgets.settings import MiAZAppSettings
from MiAZ.frontend.desktop.widgets.settings import MiAZRepoSettings
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassDelete

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
        GObject.signal_new('rename-dialog-built',
                            MiAZActions,
                            GObject.SignalFlags.RUN_LAST,
                            None, (GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT))

    def document_display(self, doc):
        self.log.debug(f"Displaying {doc}")
        repository = self.app.get_service('repo')
        filepath = os.path.join(repository.docs, doc)
        self.util.filename_display(filepath)

    def document_display_selected(self, *args):
        if self.stop_if_no_items():
            return
        workspace = self.app.get_widget('workspace')
        item = workspace.get_selected_items()[0]
        self.document_display(item.id)

    def document_delete(self, *args):
        if self.stop_if_no_items():
            return
        workspace = self.app.get_widget('workspace')
        repository = self.app.get_service('repo')
        items = workspace.get_selected_items()
        box, view = self.factory.create_view(MiAZColumnViewMassDelete)
        citems = [File(id=item.id, title=os.path.basename(item.id)) for item in items]
        view.update(citems)
        window = self.app.get_widget('window')
        title = _('Delete {count} documents?').format(count=len(items))
        body = _('The following documents will be permanently deleted:')
        dialog = self.srvdlg.show_confirmation(
            title=title, body=body, widget=box, confirm_label=_('Delete'),
            width=600, height=480)
        dialog.connect('response', self._on_document_delete_response, items)
        dialog.present(window)

    def _on_document_delete_response(self, dialog, response, items):
        if response == 'apply':
            repository = self.app.get_service('repo')
            filepaths = {os.path.join(repository.docs, item.id) for item in items}
            self.util.filename_delete(filepaths)
            body = _('{num_docs} documents deleted from repository').format(num_docs=len(items))
            self.srvdlg.show_toast(body)

    def document_rename(self, *args):
        if self.stop_if_no_items():
            return
        workspace = self.app.get_widget('workspace')
        item = workspace.get_selected_items()[0]
        self._document_rename_single(item.id)

    def _document_rename_single(self, doc):
        rename_widget = self.app.add_widget('rename-widget', MiAZRenameDialog(self.app))
        rename_widget.set_data(doc)
        window = self.app.get_widget('window')
        # A real top-level window (not Adw.AlertDialog, which is an in-window
        # overlay) so the rename dialog moves freely, even to another monitor.
        # It is transient for the main window so it stays above it, but it is
        # deliberately NOT set_modal(True): GNOME's "attach-modal-dialogs"
        # glues a modal+transient window to the parent titlebar so it moves
        # with the parent, which is exactly what we want to avoid. Instead we
        # disable the main window while the dialog is open, so the user cannot
        # work in it, and re-enable it when the dialog closes.
        dialog = MiAZWindowDialog(self.app, title=_('Rename document'),
                                  widget=rename_widget, width=1024, height=640)
        # "Rename" is the primary action and must be the first button on the
        dialog.add_response('apply', _('Rename'))
        dialog.set_response_appearance('apply', Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response('apply')
        dialog.set_close_response('cancel')
        dialog.set_show_close_button(False)
        dialog.set_transient_for(window)
        window.set_sensitive(False)
        dialog.connect('closed', lambda *_a: window.set_sensitive(True))
        self.app.add_widget('dialog-rename', dialog)

        # "Cancel" lives on the left of the header bar, styled as destructive.
        btn_cancel = self.factory.create_button(
            title=_('Cancel'),
            tooltip=_('Cancel renaming'),
            css_classes=['destructive-action'],
        )
        btn_cancel.connect('clicked', lambda *_a: dialog.emit('response', 'cancel'))
        dialog.pack_header_start(btn_cancel)

        # "Suggest" fills the five metadata drop-downs from documents that share
        # the typed concept. It sits next to Rename on the bottom and is enabled
        # only once the concept (the match key) is at least two characters long.
        btn_suggest = self.factory.create_button(
            icon_name='io.github.t00m.MiAZ-edit-paste-symbolic',
            title=_('Suggest'),
            tooltip=_('Suggest metadata from documents sharing this concept'),
        )
        btn_suggest.connect('clicked', lambda *_a: rename_widget.on_suggest_metadata())

        # "Preview" opens the source document. It sits next to Suggest.
        btn_preview = self.factory.create_button(
            icon_name='io.github.t00m.MiAZ-preview',
            title=_('Preview'),
            tooltip=_('Preview this document'),
        )
        btn_preview.connect(
            'clicked',
            lambda *_a: self.document_display(rename_widget.get_filepath_source()))

        dialog.pack_action_end(btn_suggest)
        dialog.pack_action_end(btn_preview)

        def _update_suggest_sensitive(*_a):
            btn_suggest.set_sensitive(len(rename_widget.entry_concept.get_text().strip()) >= 2)
        rename_widget.entry_concept.connect('changed', _update_suggest_sensitive)
        _update_suggest_sensitive()

        self.emit('rename-dialog-built', dialog, rename_widget)
        dialog.connect('response', self._on_rename_response, rename_widget)
        dialog.present()

    def _on_rename_response(self, dialog, response, rename_widget):
        if response == 'cancel':
            dialog.close()
        elif response == 'apply':
            body = _('You are about to rename this document.\nAre you sure?')
            dialog_confirm = self.srvdlg.show_question(
                title=_('Rename document'), body=body,
                callback=self._on_answer_question_rename,
                data=(rename_widget, dialog))
            # Overlay the confirmation on the rename window, not the main one.
            dialog_confirm.present(dialog)

    def _on_answer_question_rename(self, dialog, response, data):
        rename_widget, parent_dialog = data
        if response == 'apply':
            repository = self.app.get_service('repo')
            bsource = rename_widget.get_filepath_source()
            source = os.path.join(repository.docs, bsource)
            btarget = rename_widget.get_filepath_target()
            target = os.path.join(repository.docs, btarget)
            renamed = self.util.filename_rename(source, target)
            if not renamed:
                # Present the error on the rename window (which is on top), not
                # the disabled main window, otherwise it would be hidden behind.
                self.srvdlg.show_error(
                    title=_('Rename document'),
                    body=_('Another document with the same name already exists in this repository'),
                    parent=parent_dialog)
            else:
                parent_dialog.close()
        # On 'no' the rename window stays open so the user can amend the fields.

    def dropdown_populate(self, config, dropdown, item_type, any_value=True, none_value=False, only_include: list = [], only_exclude: list = []):
        # Can be called from a 'used-updated' signal handler or directly.
        # When called from the signal, config is the emitting object; item_type overrides it.
        i_type = item_type.__gtype_name__
        config_standard = self.app.get_config(i_type)
        if config_standard is not None:
            config = config_standard
        items = config.load(config.used)
        i_title = _(item_type.__title__)

        new_items = []
        if any_value:
            new_items.append(item_type(id='Any', title=_('Any') + ' ' + i_title.lower()))
        if none_value:
            new_items.append(item_type(id='None', title=_('None') + ' ' + i_title.lower()))

        for key in items:
            accepted = True
            if len(only_include) > 0 and key not in only_include:
                accepted = False
            if len(only_exclude) > 0 and key in only_exclude:
                accepted = False

            if accepted:
                value = items[key]
                if item_type == Repository:
                    # Repository values are dicts ({'path':..., 'description':...});
                    if isinstance(value, dict):
                        desc = value.get('description', '')
                    else:
                        desc = ''
                    title = key.replace('_', ' ')
                    new_items.append(Repository(id=key, title=title, description=desc))
                else:
                    title = value
                    if len(title) == 0:
                        title = key
                    new_items.append(item_type(id=key, title=title))

        if len(new_items) == 0:
            if item_type != Repository:
                new_items.append(item_type(id='None', title=_('No data')))
            else:
                new_items.append(item_type(id='None', title=_('No repositories found')))

        model_filter = dropdown.get_model()
        model_sort = model_filter.get_model()
        model = model_sort.get_model()
        model.splice(0, model.get_n_items(), new_items)

    def import_config(self, button, item_type):
        # FIXME
        srvdlg = self.app.get_service('dialogs')
        window = button.get_root()
        title = _("Action not implemented yet")
        body = _("Import the configuration hasn't been implemented yet")
        srvdlg.show_error(title=title, body=body, parent=window)

    def export_config(self, button, item_type):
        # FIXME
        srvdlg = self.app.get_service('dialogs')
        window = button.get_root()
        title = _("Action not implemented yet")
        body = _("Export the configuration hasn't been implemented yet")
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
        title = _('Manage {item}').format(item=config_for)
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

    def show_repository_assistant(self, *args):
        """Open the guided first-run assistant to create and configure a repo."""
        from MiAZ.frontend.desktop.widgets.assistant import MiAZRepoAssistant
        existing = self.app.get_widget('window-repo-assistant')
        if existing is not None:
            existing.present()
            return existing
        window = self.app.get_widget('window')
        assistant = MiAZRepoAssistant(self.app)
        assistant.set_transient_for(window)
        assistant.present()
        return assistant

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

    def show_app_shortcuts(self, *args):
        self.show_app_help(*args)

    def show_app_help(self, *args):
        window = self.app.get_widget('window')
        shwin = self.app.get_widget('shortcutswindow')
        if shwin is None:
            xml = """<?xml version="1.0" encoding="UTF-8"?>
<interface>
  <object class="GtkShortcutsWindow" id="shortcuts-window">
    <property name="modal">1</property>
    <child>
      <object class="GtkShortcutsSection">
        <property name="section-name">general</property>
        <child>
          <object class="GtkShortcutsGroup">
            <property name="title" translatable="yes">Application</property>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title" translatable="yes">Settings</property>
                <property name="accelerator">&lt;Control&gt;s</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title" translatable="yes">Keyboard shortcuts</property>
                <property name="accelerator">&lt;Control&gt;question</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title" translatable="yes">About MiAZ</property>
                <property name="accelerator">&lt;Control&gt;b</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title" translatable="yes">Quit</property>
                <property name="accelerator">&lt;Control&gt;q</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title" translatable="yes">Help</property>
                <property name="accelerator">F1</property>
              </object>
            </child>
          </object>
        </child>
        <child>
          <object class="GtkShortcutsGroup">
            <property name="title" translatable="yes">Documents</property>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title" translatable="yes">Rename document</property>
                <property name="accelerator">&lt;Control&gt;BackSpace</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title" translatable="yes">Delete documents</property>
                <property name="accelerator">&lt;Control&gt;Delete</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title" translatable="yes">View document</property>
                <property name="accelerator">Return</property>
              </object>
            </child>
          </object>
        </child>
      </object>
    </child>
  </object>
</interface>"""
            builder = Gtk.Builder.new_from_string(xml, -1)
            shwin = builder.get_object('shortcuts-window')
            shwin.set_hide_on_close(True)
            self.app.add_widget('shortcutswindow', shwin)
        shwin.set_transient_for(window)
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
