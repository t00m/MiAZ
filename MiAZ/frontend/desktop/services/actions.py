# File: actions.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: App actions

import os
import sys
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Adw
from gi.repository import Gio
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

# Adw.ShortcutsDialog needs libadwaita 1.8; Debian 13 ships 1.7.6. Drop this
# and _build_shortcuts_fallback once every target distribution has 1.8.
ADW_SHORTCUTS_DIALOG = (1, 8)


def accelerator_label(accelerator: str) -> str:
    """'<Control>s' as the user reads it: 'Ctrl+S'.

    Gtk.accelerator_get_label is what Adw.ShortcutsDialog renders with, and
    unlike the rest of the Gtk.Shortcuts* family it is not deprecated.
    """
    parsed, key, mods = Gtk.accelerator_parse(accelerator)
    if not parsed:
        return accelerator
    return Gtk.accelerator_get_label(key, mods)

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
        # The Suggest menu: its actions, created once, and its entries, which
        # come and go with the plugins that contribute them.
        self._suggest_actions = {}
        self._suggest_items = []
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

    def build_suggest_menu(self):
        """Build (once) the Gio.Menu behind the rename dialog's Suggest button.

        Everything that proposes values for the filename fields is here, in
        sections, so it is plain which ones read the document on this machine
        and which ones send it to a model: reading the document, matching
        against documents already filed, and whatever a plugin adds.

        "Build once, resolve the current rename widget dynamically": the menu
        is shared by every rename dialog opened, and each callback reads
        whichever rename widget is current rather than closing over one.
        """
        menu = self.app.get_widget('rename-suggest-menu')
        if menu is not None:
            return menu
        menu = Gio.Menu.new()
        self.app.add_widget('rename-suggest-menu', menu)

        from_document = _('From this document')
        for name, label, callback in (
            ('rename-detect-date', _('Date'), self._on_rename_detect_date),
            ('rename-detect-country', _('Country'), self._on_rename_detect_country),
            ('rename-detect-sentby', _('Sent by'), self._on_rename_detect_sentby),
            ('rename-detect-sentto', _('Sent to'), self._on_rename_detect_sentto),
            ('rename-detect-all', _('Every field'), self._on_rename_detect_all),
        ):
            self.register_suggest_item(owner=None, name=name, label=label,
                                       callback=callback, section=from_document)

        self.register_suggest_item(
            owner=None,
            name='rename-suggest-local',
            label=_('Sharing this concept'),
            callback=self._on_rename_suggest_local,
            section=_('From documents already filed'))
        return menu

    def register_suggest_item(self, owner, name, label, callback, section=None):
        """Add an entry to the Suggest menu.

        `owner` is the plugin name, or None for a core entry, so a plugin's
        entries can be taken away again when it unloads. `section` is the
        heading it appears under, which is what tells the user whether an
        entry reads the document here or sends it somewhere. The action is
        created once and kept: the menu is rebuilt by replacing its items, not
        by re-registering actions the whole application already knows.
        """
        if name not in self._suggest_actions:
            action = Gio.SimpleAction.new(name, None)
            action.connect('activate', callback, None)
            self.app.add_action(action)
            self._suggest_actions[name] = action
        self._suggest_items = [entry for entry in self._suggest_items
                               if entry[1] != name]
        self._suggest_items.append((owner, name, label, section))
        self._rebuild_suggest_menu()

    def unregister_suggest_items(self, owner):
        """Drop every entry a plugin contributed, on unload."""
        before = len(self._suggest_items)
        self._suggest_items = [entry for entry in self._suggest_items
                               if entry[0] != owner]
        if len(self._suggest_items) != before:
            self._rebuild_suggest_menu()

    def _rebuild_suggest_menu(self):
        """Replace the menu contents in place, so every button using it
        updates without being rebuilt itself.

        Entries keep the order they were registered in, grouped under their
        section heading, which puts the core's own groups first and a plugin's
        after them.
        """
        menu = self.app.get_widget('rename-suggest-menu')
        if menu is None:
            return
        menu.remove_all()
        headings = []
        for _owner, _name, _label, heading in self._suggest_items:
            if heading not in headings:
                headings.append(heading)
        for heading in headings:
            section = Gio.Menu.new()
            for _owner, name, label, item_heading in self._suggest_items:
                if item_heading == heading:
                    section.append(label, f'app.{name}')
            if section.get_n_items() > 0:
                menu.append_section(heading, section)

    def set_suggest_item_enabled(self, name: str, enabled: bool):
        """Enable or disable one entry of the Suggest menu.

        A plugin uses this to grey its own entry out while its suggestion is
        running: contributing an entry rather than a button of its own means
        there is no button left to make insensitive.
        """
        action = self._suggest_actions.get(name)
        if action is not None:
            action.set_enabled(enabled)

    def set_suggest_local_enabled(self, enabled: bool):
        """The concept is the key the local suggestion matches on, so its entry
        is dead until there is enough of one to match. A plugin entry is not
        affected: an AI reads the document, not the concept."""
        self.set_suggest_item_enabled('rename-suggest-local', enabled)

    def _on_rename_suggest_local(self, action, param, data):
        widget = self._current_rename_widget()
        if widget is not None:
            widget.on_suggest_metadata()

    def _current_rename_widget(self):
        return self.app.get_widget('rename-widget')

    def _on_rename_detect_date(self, action, param, data):
        widget = self._current_rename_widget()
        if widget is not None:
            widget.detect_date()

    def _on_rename_detect_country(self, action, param, data):
        widget = self._current_rename_widget()
        if widget is not None:
            widget.detect_country()

    def _on_rename_detect_sentby(self, action, param, data):
        widget = self._current_rename_widget()
        if widget is not None:
            widget.detect_sentby()

    def _on_rename_detect_sentto(self, action, param, data):
        widget = self._current_rename_widget()
        if widget is not None:
            widget.detect_sentto()

    def _on_rename_detect_all(self, action, param, data):
        widget = self._current_rename_widget()
        if widget is not None:
            widget.detect_all()

    def _document_rename_single(self, doc):
        old = self.app.get_widget('rename-widget')
        if old is not None and hasattr(old, 'dispose'):
            old.dispose()
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
        dialog.pack_action_start(btn_cancel)

        # One button for everything that proposes field values, in sections so
        # a local guess reads differently from one sent to a model.
        btn_suggest = Gtk.MenuButton()
        btn_suggest.set_child(Adw.ButtonContent(
            icon_name='io.github.t00m.MiAZ-edit-paste-symbolic',
            label=_('Suggest')))
        btn_suggest.set_always_show_arrow(True)
        btn_suggest.set_tooltip_text(_('Suggest values for the filename fields'))
        btn_suggest.set_menu_model(self.build_suggest_menu())

        # "Preview" opens the source document. It sits next to Suggest.
        btn_preview = self.factory.create_button(
            icon_name='io.github.t00m.MiAZ-preview',
            title=_('Preview'),
            tooltip=_('Preview this document'),
        )
        btn_preview.connect(
            'clicked',
            lambda *_a: self.document_display(rename_widget.get_filepath_source()))

        # Right of the header, where the plugin's own AI button used to be.
        dialog.pack_header_end(btn_suggest)

        # Fields page only: it cannot propose a project or a periodicity, so
        # elsewhere it would offer to fill in fields that are not shown.
        def _suggest_visible(*_a):
            btn_suggest.set_visible(
                rename_widget.stack.get_visible_child_name() == 'fields')
        rename_widget.stack.connect('notify::visible-child', _suggest_visible)
        _suggest_visible()
        dialog.pack_action_end(btn_preview)

        def _update_suggest_sensitive(*_a):
            # The menu button stays usable: a plugin entry may not need a
            # concept. Only the local entry, which matches on it, goes dead.
            self.set_suggest_local_enabled(
                len(rename_widget.entry_concept.get_text().strip()) >= 2)
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

    def dropdown_populate(self, config, dropdown, item_type, any_value=True, none_value=False, only_include=None, only_exclude=None):
        # Called directly, or through dropdown_repopulate from a config signal.
        # From the signal, config is the emitting object; item_type overrides it.
        if only_include is None:
            only_include = []
        if only_exclude is None:
            only_exclude = []
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
        about.present(window)

    def show_app_shortcuts(self, *args):
        self.show_app_help(*args)

    def shortcut_sections(self):
        """The shortcuts, written once.

        Both builders read this, so the two cannot list different keys. Built
        on each call rather than at import, so the titles are translated in the
        language in use rather than the one loaded first.
        """
        return (
            (_('Application'), (
                (_('Settings'), '<Control>s'),
                (_('Keyboard shortcuts'), '<Control>question'),
                (_('About MiAZ'), '<Control>b'),
                (_('Quit'), '<Control>q'),
                (_('Help (this window)'), 'F1'),
            )),
            (_('Documents'), (
                (_('Rename document'), '<Control>BackSpace'),
                (_('Delete documents'), '<Control>Delete'),
                (_('View document'), 'Return'),
            )),
        )

    def show_app_help(self, *args):
        window = self.app.get_widget('window')
        sections = self.shortcut_sections()
        if (Adw.MAJOR_VERSION, Adw.MINOR_VERSION) >= ADW_SHORTCUTS_DIALOG:
            dialog = self._build_shortcuts_dialog(sections)
        else:
            dialog = self._build_shortcuts_fallback(sections)
        dialog.present(window)

    def _build_shortcuts_dialog(self, sections):
        """The native dialog: adaptive, and styled like the rest of the app."""
        dialog = Adw.ShortcutsDialog()
        for title, shortcuts in sections:
            section = Adw.ShortcutsSection(title=title)
            for label, accelerator in shortcuts:
                section.add(Adw.ShortcutsItem(title=label, accelerator=accelerator))
            dialog.add(section)
        return dialog

    def _build_shortcuts_fallback(self, sections):
        """The same list on libadwaita older than 1.8.

        Built from Adw.PreferencesPage rather than Gtk.ShortcutsWindow: that
        whole family is deprecated as of GTK 4.18 and is what MiAZ moved away
        from in the first place. Everything here exists in 1.4 and earlier.
        """
        dialog = Adw.Dialog()
        dialog.set_title(_('Keyboard shortcuts'))
        dialog.set_content_width(460)
        dialog.set_content_height(520)
        page = Adw.PreferencesPage()
        for title, shortcuts in sections:
            group = Adw.PreferencesGroup(title=title)
            for label, accelerator in shortcuts:
                row = Adw.ActionRow(title=label)
                keys = Gtk.Label(label=accelerator_label(accelerator))
                keys.add_css_class('dim-label')
                row.add_suffix(keys)
                group.add(row)
            page.add(group)
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        toolbar.set_content(page)
        dialog.set_child(toolbar)
        return dialog

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
        self._close_all_webviews()
        self.app.emit("application-finished")
        self.app.quit()

    def _close_webviews(self, widget):
        """Stop every WebKit web process under this widget before quitting.

        WebKit runs each view in its own subprocess holding a D-Bus name. Quit
        without stopping them and the bus connection goes first, so the child
        complains on the way out:

            Error releasing name ...WebProcess-<uuid>: The connection is closed

        try_close() alone does not prevent it: it asks the page to close, runs
        beforeunload and returns immediately, so the process is still up when
        the main loop stops. terminate_web_process() is the one that ends the
        subprocess there and then. The warning comes from the child, so the
        parent can never catch it, only avoid causing it.
        """
        if widget.__gtype__.name == 'WebKitWebView':
            for method in ('try_close', 'terminate_web_process'):
                action = getattr(widget, method, None)
                if action is None:
                    continue
                try:
                    action()
                except Exception as error:
                    self.log.debug(f"WebView {method} failed: {error}")
        if hasattr(widget, 'get_first_child'):
            child = widget.get_first_child()
            while child is not None:
                nxt = child.get_next_sibling()
                self._close_webviews(child)
                child = nxt

    def _close_all_webviews(self):
        for window in Gtk.Window.get_toplevels():
            self._close_webviews(window)

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
        self._close_all_webviews()
        self.app.emit('application-finished')
        self.log.info(f"Application restart: {python} {script} {sys.argv[1:]}")
        os.execv(python, [python, script] + sys.argv[1:])
