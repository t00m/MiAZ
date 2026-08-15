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
from gi.repository import Gdk

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.util import humanize_value
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
        btn_rename = dialog.add_response('apply', _('Rename'))
        dialog.set_response_appearance('apply', Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response('apply')
        dialog.set_close_response('cancel')
        dialog.set_show_close_button(False)
        # With plugin tabs registered, the header bar carries the view switcher
        # instead of the window title.
        switcher = rename_widget.get_switcher()
        if switcher is not None:
            dialog.set_title_widget(switcher)
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

        # "Rename" stays insensitive while the fields cannot make a valid
        # filename. Clicking it used to do nothing visible: the handler refused
        # the rename and focused the offending field, which reads as a dead
        # button. Group and Purpose are advisory and do not block, so they are
        # not part of the condition (see MiAZRenameDialog.is_valid).
        def _update_rename_sensitive(*_a):
            valid = rename_widget.is_valid()
            dialog.set_response_enabled('apply', valid)
            btn_rename.set_tooltip_text(
                _('Rename this document') if valid
                else _('Fill in date, country, sent by, concept and sent to first'))
        rename_widget.connect('fields-changed', _update_rename_sensitive)
        _update_rename_sensitive()

        # Focus the first field that needs attention when the dialog is shown.
        rename_widget.connect('map', rename_widget.focus_first_field)

        # Ctrl+Enter always applies, from any field. Capture phase so it fires
        # before an entry or dropdown can consume the key.
        accel = Gtk.EventControllerKey()
        accel.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)

        def _on_apply_accel(_c, keyval, _kc, state):
            if (state & Gdk.ModifierType.CONTROL_MASK) and keyval in (
                    Gdk.KEY_Return, Gdk.KEY_KP_Enter):
                dialog.emit('response', 'apply')
                return True
            return False

        accel.connect('key-pressed', _on_apply_accel)
        dialog.add_controller(accel)

        self.emit('rename-dialog-built', dialog, rename_widget)
        dialog.connect('response', self._on_rename_response, rename_widget)
        dialog.present()

    def _on_rename_response(self, dialog, response, rename_widget):
        if response == 'cancel':
            # Plugin tabs hold their edits until the rename goes through, so
            # cancelling drops them the same way it drops the field changes.
            rename_widget.discard_tabs()
            dialog.close()
        elif response == 'apply':
            if not rename_widget.is_valid():
                # Refuse to build an invalid filename. Keep the dialog open and
                # point the user at the first field that needs fixing.
                rename_widget.focus_first_field()
                return
            valid, tab_name = rename_widget.tabs_valid()
            if not valid:
                # A plugin tab refuses the rename: show it so the user can see why.
                rename_widget.focus_tab(tab_name)
                return
            if not rename_widget.name_changes():
                # Every filename field was left alone: the document was opened
                # to edit what a plugin tab holds (a project, a periodicity).
                # There is nothing to rename, and nothing destructive to
                # confirm, so the tab edits are written and the dialog closes.
                doc = os.path.basename(rename_widget.get_filepath_source())
                if rename_widget.commit_tabs(doc, doc):
                    self.srvdlg.show_toast(_('Document properties saved'))
                dialog.close()
                return
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
                # The rename emitted 'filename-renamed', so plugins have already
                # moved their per-document data to the new name. Only now do the
                # tabs write what the user changed, against that new name.
                rename_widget.commit_tabs(os.path.basename(bsource),
                                          os.path.basename(btarget))
                parent_dialog.close()
        # On 'no' the rename window stays open so the user can amend the fields.

    def dropdown_repopulate(self, config, changed, dropdown, item_type,
                            any_value=True, none_value=False):
        """Signal adapter for 'used-updated' and 'available-updated'.

        Both signals pass the set of keys that changed. Rebuilding a dropdown
        reads the whole file anyway, so the payload is dropped here rather than
        threaded through dropdown_populate, which is also called directly.
        """
        self.dropdown_populate(config, dropdown, item_type, any_value, none_value)

    def dropdown_populate(self, config, dropdown, item_type, any_value=True, none_value=False, only_include: list = [], only_exclude: list = []):
        # Called directly, or through dropdown_repopulate from a config signal.
        # From the signal, config is the emitting object; item_type overrides it.
        i_type = item_type.__gtype_name__
        config_standard = self.app.get_config(i_type)
        if config_standard is not None:
            config = config_standard
        items = config.load(config.used)
        i_title = _(item_type.__title__)

        # Special entries ('Any'/'None') stay pinned on top; real values are
        # sorted alphabetically below, ignoring case.
        special_items = []
        if any_value:
            special_items.append(item_type(id='Any', title=_('Any') + ' ' + i_title.lower()))
        if none_value:
            special_items.append(item_type(id='None', title=_('None') + ' ' + i_title.lower()))

        value_items = []
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
                    value_items.append(Repository(id=key, title=title, description=desc))
                else:
                    title = humanize_value(i_type, value)
                    if len(title) == 0:
                        title = key
                    value_items.append(item_type(id=key, title=title))

        value_items.sort(key=lambda item: item.title.casefold())
        new_items = special_items + value_items

        if len(new_items) == 0:
            if item_type != Repository:
                new_items.append(item_type(id='None', title=_('No data')))
            else:
                new_items.append(item_type(id='None', title=_('No repositories found')))

        model_filter = dropdown.get_model()
        model_sort = model_filter.get_model()
        model = model_sort.get_model()
        model.splice(0, model.get_n_items(), new_items)

    def manage_resource(self, widget: Gtk.Widget, view):
        """Open a management view for one vocabulary.

        `view` is normally the class. It used to be an instance, built once
        when the button was connected and packed into a new dialog on every
        click: the first dialog took ownership of it, so the second one showed
        an empty box until the whole rename dialog was closed and rebuilt.
        Building it here means every click gets a live view. An instance is
        still accepted, and taken back from its previous dialog first, so a
        plugin passing one keeps working.
        """
        factory = self.app.get_service('factory')
        parent = widget.get_root() # wonderful

        selector = view(self.app) if isinstance(view, type) else view
        if selector.get_parent() is not None:
            selector.unparent()

        box = factory.create_box_vertical(spacing=0, vexpand=True, hexpand=True)
        box.append(selector)
        config_for = selector.get_config_for()
        selector.set_vexpand(True)
        selector.update_views()
        title = _('Manage {item}').format(item=config_for)
        # This is an immediate-apply management view: the selector persists every
        # enable/disable change live, so there is nothing to Cancel or Apply. A
        # window with the standard headerbar close button (and Escape) is the
        # right close affordance; no bottom Cancel/Apply buttons.
        dialog = MiAZWindowDialog(self.app, title=title, widget=box,
                                  width=800, height=600)
        dialog.set_show_close_button(True)
        self.app.add_widget('dialog-manage-resource', dialog)
        dialog.present(parent)
        return dialog

    def show_app_settings(self, *args):
        window = self.app.get_widget('window')
        dialog_app_settings = MiAZAppSettings(self.app)
        dialog_app_settings.present(window)
        self.app.add_widget('window-settings', dialog_app_settings)
        self.emit('settings-loaded', dialog_app_settings)

    def show_repository_settings(self, *args):
        try:
            # Continue if a default repository exists
            repo_id = self.app.get_service('repo').get_active_id().replace('_', ' ')
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
        # Adw.ShortcutsDialog (libadwaita 1.8+) replaces the deprecated
        # Gtk.ShortcutsWindow. It is adaptive and matches the app dialog style.
        window = self.app.get_widget('window')
        dialog = Adw.ShortcutsDialog()

        app_section = Adw.ShortcutsSection(title=_('Application'))
        for title, accelerator in (
            (_('Settings'), '<Control>s'),
            (_('Keyboard shortcuts'), '<Control>question'),
            (_('About MiAZ'), '<Control>b'),
            (_('Quit'), '<Control>q'),
            (_('Help (this window)'), 'F1'),
        ):
            app_section.add(Adw.ShortcutsItem(title=title, accelerator=accelerator))
        dialog.add(app_section)

        docs_section = Adw.ShortcutsSection(title=_('Documents'))
        for title, accelerator in (
            (_('Rename document'), '<Control>BackSpace'),
            (_('Delete documents'), '<Control>Delete'),
            (_('View document'), 'Return'),
        ):
            docs_section.add(Adw.ShortcutsItem(title=title, accelerator=accelerator))
        dialog.add(docs_section)

        dialog.present(window)

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
