# File: rename.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Rename widget for single items

import os
from datetime import datetime
from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import Pango

from MiAZ.env import ENV
from MiAZ.backend.log import MiAZLog
from MiAZ.backend.util import humanize_value
from MiAZ.backend.models import MiAZItem, Group, Country, Purpose, Concept, SentBy, SentTo
from MiAZ.frontend.desktop.services.dialogs import MiAZDialogAdd
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries, MiAZGroups, MiAZPurposes, MiAZPeopleSentBy, MiAZPeopleSentTo
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewConcept
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewSuggestion


class MiAZRenameDialog(Gtk.Box):
    __gtype_name__ = 'MiAZRenameDialog'
    __gsignals__ = {
        # Any filename field changed. Carries nothing: what a receiver needs is
        # is_valid(), which reads the fields anyway.
        'fields-changed': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, app) -> Gtk.Widget:
        super(MiAZRenameDialog, self).__init__(orientation=Gtk.Orientation.VERTICAL, spacing=3, hexpand=True, vexpand=True)
        self.app = app
        self.factory = self.app.get_service('factory')
        self.actions = self.app.get_service('actions')
        self.icons = self.app.get_service('icons')
        self.repository = self.app.get_service('repo')
        self.config = self.app.get_config_dict()
        self.util = self.app.get_service('util')
        self.srvdlg = self.app.get_service('dialogs')
        self.log = MiAZLog('Miaz.Rename')
        self.result = ''
        self.new_values = []
        self.dropdown = {}
        self._last_date_str = None
        self._last_date_valid = False
        self._cfg_country = self.app.get_config('Country')
        self._cfg_group = self.app.get_config('Group')
        self._cfg_sentby = self.app.get_config('SentBy')
        self._cfg_purpose = self.app.get_config('Purpose')
        self._cfg_sentto = self.app.get_config('SentTo')

        # Box to be inserted as contents
        self.boxMain = Gtk.ListBox.new()
        self.boxMain.set_vexpand(True)
        self.boxMain.set_hexpand(True)

        # Filename format: {timestamp}-{country}-{group}-{sentby}-{purpose}-{concept}-{sentto}.{extension}
        self.__create_field_0_date() # Field 0. Date
        self.__create_field_1_country() # Field 1. Country
        self.__create_field_2_group() # Field 2. Group
        self.__create_field_4_sentby() # Field 4. Sent by
        self.__create_field_5_purpose() # Field 5. Purpose
        self.__create_field_6_concept() # Field 6. Concept
        self.__create_field_7_sentto() # Field 7. Sent to
        self.__create_field_8_extension() # Field 8. Extension

        frmMain = Gtk.Frame()
        frmMain.set_margin_top(margin=6)
        frmMain.set_margin_end(margin=6)
        frmMain.set_margin_bottom(margin=6)
        frmMain.set_margin_start(margin=6)
        frmMain.set_child(self.boxMain)

        # The fields are the first page of a view stack. Plugins contribute the
        # rest through the 'document-tabs' registry; with none registered the
        # switcher is never installed and the dialog looks as it always did.
        self.stack = Adw.ViewStack()
        self.stack.set_vexpand(True)
        self.stack.set_hexpand(True)
        page = self.stack.add_titled(frmMain, 'fields', _('Fields'))
        # Plugin tabs carry their plugin's icon, so the first page needs one too
        # or the switcher shows a bare label next to icons.
        page.set_icon_name('io.github.t00m.MiAZ-rename')
        self.append(self.stack)
        self.plugin_tabs = []
        self.switcher = None
        self.__create_plugin_tabs()

        # The filename preview is the outcome of the dialog, so it sits under
        # the stack and stays visible whatever tab is open.
        self.__create_filename_footer()

        self.config['Country'].connect('used-updated', self.update_dropdown, Country)
        self.config['Group'].connect('used-updated', self.update_dropdown, Group)
        self.config['SentBy'].connect('used-updated', self.update_dropdown, SentBy)
        self.config['Purpose'].connect('used-updated', self.update_dropdown, Purpose)
        self.config['SentTo'].connect('used-updated', self.update_dropdown, SentTo)
        repository = self.app.get_service('repo')
        repository.connect('repository-switched', self._update_dropdowns)

    def _update_dropdowns(self, *args):
        for item_type in [Country, Group, SentBy, Purpose, SentTo]:
            i_type = item_type.__gtype_name__
            config = self.config[i_type]
            self.actions.dropdown_populate(config, self.dropdown[i_type], item_type, False, False)

    def update_dropdown(self, config, changed, item_type):
        # 'changed' is the key set the config signal carries. Repopulating reads
        # the whole file, so it is not needed here.
        title = item_type.__gtype_name__
        self.actions.dropdown_populate(config, self.dropdown[title], item_type)
        self._on_changed_entry()

    def set_data(self, doc):
        self.doc = doc
        self.filepath = doc
        name, self.extension = self.util.filename_details(doc)
        filepath = os.path.join(self.repository.docs, doc)
        self.suggested = self.util.get_fields(self.doc)
        if len(self.suggested[0]) == 0:
            adate = self.guess_date_if_empty(self.suggested[5], filepath)
            self.entry_date.set_text(adate)
        else:
            self.entry_date.set_text(self.suggested[0])
        self._set_suggestion(self.dpdCountry, self.suggested[1])
        self._set_suggestion(self.dpdGroup, self.suggested[2])
        self._set_suggestion(self.dpdSentBy, self.suggested[3])
        self._set_suggestion(self.dpdPurpose, self.suggested[4])
        if len(self.suggested[5]) > 0:
            self._set_concept_text(self.suggested[5])
        self._set_suggestion(self.dpdSentTo, self.suggested[6])
        self.lblExt.set_text(self.extension)
        self.lblFilenameCur.set_text(os.path.basename(self.doc))
        self.lblFilenameCur.set_selectable(True)
        self.lblFilenameNew.set_text(self.result)
        self.lblFilenameNew.set_selectable(True)
        self._on_changed_entry()
        for _name, _result in self._each_tab('set_document', os.path.basename(doc)):
            pass

    def is_valid(self) -> bool:
        """True when the required fields form a valid filename. Group and
        Purpose are advisory (warnings in the live preview) and do not block;
        Date, Country, Sent by, Concept and Sent to must be valid."""
        return (
            self.validate_date(self.entry_date.get_text())
            and self._cfg_country.exists_used(self._dropdown_get_id(self.dpdCountry))
            and self._cfg_sentby.exists_used(self._dropdown_get_id(self.dpdSentBy))
            and len(self.util.valid_key(self.entry_concept.get_text().upper())) > 0
            and self._cfg_sentto.exists_used(self._dropdown_get_id(self.dpdSentTo))
        )

    def focus_first_field(self, *args):
        """Focus the first field that needs attention (empty or invalid) in
        filename order; if all are valid, focus the concept entry. Returns False
        so it can be used directly as a 'map' signal handler."""
        checks = [
            (self.validate_date(self.entry_date.get_text()), self.entry_date),
            (self._cfg_country.exists_used(self._dropdown_get_id(self.dpdCountry)), self.dpdCountry),
            (self._cfg_group.exists_used(self._dropdown_get_id(self.dpdGroup)), self.dpdGroup),
            (self._cfg_sentby.exists_used(self._dropdown_get_id(self.dpdSentBy)), self.dpdSentBy),
            (self._cfg_purpose.exists_used(self._dropdown_get_id(self.dpdPurpose)), self.dpdPurpose),
            (len(self.util.valid_key(self.entry_concept.get_text().upper())) > 0, self.entry_concept),
            (self._cfg_sentto.exists_used(self._dropdown_get_id(self.dpdSentTo)), self.dpdSentTo),
        ]
        for valid, widget in checks:
            if not valid:
                widget.grab_focus()
                return False
        self.entry_concept.grab_focus()
        return False

    def get_filename_widget(self):
        return self.lblFilenameCur

    def __create_box_value(self) -> Gtk.Box:
        box = Gtk.Box.new(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.set_hexpand(False)
        box.set_valign(Gtk.Align.CENTER)
        return box

    def __setup_button_suggest_concept(self) -> Gtk.Box:
        def choose_concept(button, view, rename_widget):
            window = rename_widget.get_root()
            body = ''
            dialog = self.srvdlg.show_question(title=_('Choose a concept'), body=body, widget=view, width=600, height=480)
            dialog.connect('response', dialog_response, view)
            dialog.present(window)

        def dialog_response(dialog, response, widget):
            if response == 'apply':
                view = self.app.get_widget('window-rename-view-concepts')
                try:
                    item = view.get_selected()
                    self._set_concept_text(item.title)
                except IndexError as error:
                    self.log.error(error)

        def on_filter_concepts_view(*args):
            view = self.app.get_widget('window-rename-view-concepts')
            view.refilter()

        def do_filter_view(item, filter_list_model):
            left = searchentry.get_text()
            return left.upper() in item.title.upper()


        widget = self.factory.create_box_vertical(hexpand=True, vexpand=True)
        searchentry = Gtk.SearchEntry()
        self.app.add_widget('window-rename-searchentry-concepts', searchentry)
        searchentry.connect('changed', on_filter_concepts_view)
        frame = Gtk.Frame()
        view = MiAZColumnViewConcept(self.app)
        self.app.add_widget('window-rename-view-concepts', view)
        view.set_filter(do_filter_view)
        view.column_id.set_visible(False)
        view.column_title.set_expand(True)
        frame.set_child(view)
        button = self.factory.create_button(title='Use concept')
        widget.append(searchentry)
        widget.append(frame)

        items = []
        for concept in ENV['CACHE']['CONCEPTS']['ACTIVE']:
            items.append(Concept(id='', title=concept))
        view.update(items)

        button = self.factory.create_button(icon_name='io.github.t00m.MiAZ-edit-paste-symbolic',
                                            tooltip='Reuse a concept for this document'
                                            )
        button.connect('clicked', choose_concept, widget, self)
        return button

    def __create_actionrow(self, title, item_type, conf, conf_obj=None) -> Gtk.Widget:
        i_title = item_type.__config_name__
        icon_name = f"io.github.t00m.MiAZ-res-{i_title.lower().replace(' ', '')}"
        icon = self.icons.get_image_by_name(name=icon_name)
        boxValue = self.__create_box_value()
        btn_add = self.factory.create_button(
            icon_name='list-add-symbolic',
            tooltip=_('Add a new {title} to this repository').format(title=i_title.lower()),
            css_classes=['flat'],
        )
        if conf_obj is not None:
            btn_add.connect('clicked', self._on_inline_add_value, item_type, conf_obj)
        else:
            btn_add.set_sensitive(False)
        button = self.factory.create_button(icon_name=icon_name, title='')
        dropdown = self.factory.create_dropdown_generic(item_type, ellipsize=False) #, item)
        self.actions.dropdown_populate(conf, dropdown, item_type)
        boxValue.append(dropdown)
        boxValue.append(btn_add)
        boxValue.append(button)
        row = self.factory.create_actionrow(title, prefix=icon, suffix=boxValue)
        self.boxMain.append(row)
        return row, button, dropdown

    def _set_suggestion(self, dropdown, suggestion):
        if suggestion:
            model = dropdown.get_model()
            for n, item in enumerate(model):
                if item.id == suggestion:
                    dropdown.set_selected(n)
                    return
        dropdown.set_selected(0)

    # Suggest metadata from documents sharing the typed concept
    def _collect_metadata_suggestions(self, concept_text):
        """Return one representative MiAZItem per distinct metadata combination
        (country, group, purpose, sentby, sentto) among every document in the
        repository whose concept contains the typed text.

        The whole repository is scanned directly (not the workspace view, which
        may be filtered). Matching is done on the canonical concept token:
        valid_key turns spaces and hyphens into underscores, the same transform
        the filename uses, so typing "RNR 31046" matches "RNR_31046_...".
        """
        needle = self.util.valid_key(concept_text or '').upper()
        if not needle:
            return []
        try:
            docs = self.util.get_files(self.repository.docs)
        except (KeyError, OSError):
            docs = []

        cfg = {
            1: self._cfg_country,
            2: self._cfg_group,
            3: self._cfg_sentby,
            4: self._cfg_purpose,
            6: self._cfg_sentto,
        }

        suggestions = []
        seen = set()
        for filename in docs:
            fields = self.util.get_fields(filename)
            if len(fields) < 7:
                continue
            if needle not in fields[5].upper():
                continue
            combo = (fields[1], fields[2], fields[4], fields[3], fields[6])
            if combo in seen:
                continue
            seen.add(combo)

            idx_field = {1: 'Country', 2: 'Group', 3: 'SentBy', 4: 'Purpose', 6: 'SentTo'}

            def describe(idx):
                key = fields[idx]
                if not key:
                    return ''
                description = cfg[idx].get(key)
                description = description if description is not None else key
                return humanize_value(idx_field.get(idx, ''), description)

            suggestions.append(MiAZItem(
                id=os.path.basename(filename),
                country=fields[1], country_dsc=describe(1),
                group=fields[2], group_dsc=describe(2),
                sentby_id=fields[3], sentby_dsc=describe(3),
                purpose=fields[4], purpose_dsc=describe(4),
                sentto_id=fields[6], sentto_dsc=describe(6),
                title=os.path.basename(filename),
                subtitle=fields[5].replace('_', ' '),
            ))
        return suggestions

    def on_suggest_metadata(self):
        items = self._collect_metadata_suggestions(self.entry_concept.get_text())
        if not items:
            self.srvdlg.show_info(
                title=_('No suggestions'),
                body=_('No other documents share this concept yet.'))
            return
        view = MiAZColumnViewSuggestion(self.app)
        self.app.add_widget('rename-view-suggestions', view)
        view.update(items)
        dialog = self.srvdlg.show_question(
            title=_('Suggested metadata'), body='', widget=view, width=720, height=480)
        dialog.connect('response', self._on_suggestion_response)
        dialog.present(self.get_root())

    def _on_suggestion_response(self, dialog, response):
        if response != 'apply':
            return
        view = self.app.get_widget('rename-view-suggestions')
        item = view.get_selected()
        if item is None:
            return
        self._set_suggestion(self.dpdCountry, item.country)
        self._set_suggestion(self.dpdGroup, item.group)
        self._set_suggestion(self.dpdSentBy, item.sentby_id)
        self._set_suggestion(self.dpdPurpose, item.purpose)
        self._set_suggestion(self.dpdSentTo, item.sentto_id)
        self._on_changed_entry()

    def __create_field_0_date(self):
        """Field 0. Date"""
        icm = self.app.get_service('icons')
        title = _('Date')
        icon_name = 'io.github.t00m.MiAZ-res-date'
        prefix = icm.get_image_by_name(icon_name)
        boxValue = self.__create_box_value()
        boxValue.set_hexpand(False)
        boxValue.set_valign(Gtk.Align.CENTER)
        self.rowDate = self.factory.create_actionrow(title=title, prefix=prefix, suffix=boxValue)
        self.boxMain.append(self.rowDate)
        self.calendar = Gtk.Calendar()
        self.calendar.connect('day-selected', self.calendar_day_selected)
        button_content = self.factory.create_button_content(icon_name=icon_name)
        button = Gtk.MenuButton(child=button_content)
        popover = Gtk.Popover()
        popover.set_child(self.calendar)
        popover.present()
        button.set_popover(popover)
        self.label_date = Gtk.Label()
        self.label_date.add_css_class('caption')
        self.entry_date = Gtk.Entry()
        self.entry_date.set_activates_default(True)
        self.entry_date.set_max_length(8)
        self.entry_date.set_max_width_chars(12)
        self.entry_date.set_width_chars(12)
        self.entry_date.set_placeholder_text(_('YYYYmmdd'))
        self.entry_date.set_alignment(1.0)
        boxValue.append(self.label_date)
        boxValue.append(self.entry_date)
        boxValue.append(button)
        self.entry_date.connect('changed', self._on_changed_entry)

    def guess_date_if_empty(self, concept: str, filepath: str):
        return self.util.filename_guess_date(filepath, concept_hint=concept)

    def calendar_day_selected(self, calendar):
        adate = calendar.get_date()
        y = "%04d" % adate.get_year()
        m = "%02d" % adate.get_month()
        d = "%02d" % adate.get_day_of_month()
        self.entry_date.set_text(f"{y}{m}{d}")

    def __create_field_1_country(self):
        self.rowCountry, self.btnCountry, self.dpdCountry = self.__create_actionrow(_(Country.__title__), Country, 'countries', self._cfg_country)
        self.dropdown['Country'] = self.dpdCountry
        self.btnCountry.connect('clicked', self.actions.manage_resource, MiAZCountries(self.app))
        self.dpdCountry.connect("notify::selected-item", self._on_changed_entry)

    def __create_field_2_group(self):
        self.rowGroup, self.btnGroup, self.dpdGroup = self.__create_actionrow(_(Group.__title__), Group, 'groups', self._cfg_group)
        self.dropdown['Group'] = self.dpdGroup
        self.btnGroup.connect('clicked', self.actions.manage_resource, MiAZGroups(self.app))
        self.dpdGroup.connect("notify::selected-item", self._on_changed_entry)

    def __create_field_4_sentby(self):
        self.rowSentBy, self.btnSentBy, self.dpdSentBy = self.__create_actionrow(_(SentBy.__title__), SentBy, 'Sentby', self._cfg_sentby)
        self.dropdown['SentBy'] = self.dpdSentBy
        self.btnSentBy.connect('clicked', self.actions.manage_resource, MiAZPeopleSentBy(self.app))
        self.dpdSentBy.connect("notify::selected-item", self._on_changed_entry)

    def __create_field_5_purpose(self):
        self.rowPurpose, self.btnPurpose, self.dpdPurpose = self.__create_actionrow(_(Purpose.__title__), Purpose, 'purposes', self._cfg_purpose)
        self.btnPurpose.connect('clicked', self.actions.manage_resource, MiAZPurposes(self.app))
        self.dropdown['Purpose'] = self.dpdPurpose
        self.dpdPurpose.connect("notify::selected-item", self._on_changed_entry)

    def __create_field_6_concept(self):
        """Field 6. Concept"""
        title = _(Concept.__title__)
        icm = self.app.get_service('icons')
        icon_name = 'io.github.t00m.MiAZ-res-concept'
        prefix = icm.get_image_by_name(icon_name)
        boxValue = self.__create_box_value()
        self.rowConcept = self.factory.create_actionrow(title=title, prefix=prefix, suffix= boxValue)
        self.boxMain.append(self.rowConcept)
        button = self.__setup_button_suggest_concept()
        self.entry_concept = Gtk.Entry()
        self.entry_concept.set_activates_default(True)
        self.entry_concept.set_width_chars(41)
        self.entry_concept.set_placeholder_text(_('Type to filter existing concepts…'))
        boxValue.append(self.entry_concept)
        boxValue.append(button)

        # Autocomplete popover anchored to the concept entry.
        # autohide=False keeps the entry focused while the popover is up
        # (otherwise the popover would steal keystrokes). Closing paths
        # are explicit: pick a row, press Escape, leave focus, clear entry.
        self._concept_popover = Gtk.Popover()
        self._concept_popover.set_parent(self.entry_concept)
        self._concept_popover.set_autohide(False)
        self._concept_popover.set_has_arrow(False)
        self._concept_popover.set_position(Gtk.PositionType.BOTTOM)
        self._concept_list_store = Gio.ListStore(item_type=Concept)
        self._concept_selection = Gtk.SingleSelection.new(self._concept_list_store)
        self._concept_list_view = Gtk.ListView(model=self._concept_selection)
        self._concept_list_view.set_single_click_activate(True)
        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', self._concept_factory_setup)
        factory.connect('bind', self._concept_factory_bind)
        self._concept_list_view.set_factory(factory)
        self._concept_list_view.connect('activate', self._on_concept_picked)

        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_width(300)
        scroll.set_min_content_height(200)
        scroll.set_child(self._concept_list_view)
        self._concept_popover.set_child(scroll)

        self._concept_throttle_id = 0
        self._concept_loading = False
        self.entry_concept.connect('changed', self._on_concept_entry_changed)
        self.entry_concept.connect('changed', self._on_changed_entry)

        # Escape closes the popover; Enter picks the highlighted concept when
        # the popover is open. Capture phase so this runs before the entry's
        # internal GtkText, which otherwise consumes Return for its own
        # activate (firing the dialog default) before it can reach us.
        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_ctrl.connect('key-pressed', self._on_concept_key_pressed)
        self.entry_concept.add_controller(key_ctrl)

        # Focus-leave closes it too, with a small grace period so that
        # clicks landing on a popover row register first.
        focus_ctrl = Gtk.EventControllerFocus()
        focus_ctrl.connect('leave', self._on_concept_focus_leave)
        self.entry_concept.add_controller(focus_ctrl)

    def __create_field_7_sentto(self):
        self.rowSentTo, self.btnSentTo, self.dpdSentTo = self.__create_actionrow(_(SentTo.__title__), SentTo, 'SentTo', self._cfg_sentto)
        self.dropdown['SentTo'] = self.dpdSentTo
        self.btnSentTo.connect('clicked', self.actions.manage_resource, MiAZPeopleSentTo(self.app))
        self.dpdSentTo.connect("notify::selected-item", self._on_changed_entry)

    def __create_field_8_extension(self):
        """Field 7. extension"""

        title = _('Extension')
        icon_name = 'io.github.t00m.MiAZ-res-extension'
        icon = self.icons.get_image_by_name(name=icon_name)
        boxValue = self.__create_box_value()
        self.rowExt = self.factory.create_actionrow(title=title, prefix=icon, suffix=boxValue)
        self.boxMain.append(self.rowExt)
        button = self.factory.create_button('', '', css_classes=['flat'])
        button.set_sensitive(False)
        button.set_has_frame(False)
        self.lblExt = Gtk.Label()
        boxValue.append(self.lblExt)
        boxValue.append(button)

    def __create_filename_footer(self, *args):
        """Current and new filename, shown under every tab."""
        listbox = Gtk.ListBox.new()
        listbox.set_hexpand(True)

        # Current filename
        title = _('Current filename')
        self.lblFilenameCur = Gtk.Label()
        self.lblFilenameCur.add_css_class('monospace')
        self.lblFilenameCur.add_css_class('error')
        self.row_cur_filename = self.factory.create_actionrow(title=title, suffix=self.lblFilenameCur)
        listbox.append(self.row_cur_filename)
        self.lblFilenameCur.set_ellipsize(True)
        self.lblFilenameCur.set_property('ellipsize', Pango.EllipsizeMode.MIDDLE)

        # New filename
        title = _('New filename')
        self.lblFilenameNew = Gtk.Label()
        self.lblFilenameNew.add_css_class('monospace')
        self.lblFilenameNew.add_css_class('success')
        self.lblFilenameNew.set_ellipsize(True)
        self.lblFilenameNew.set_property('ellipsize', Pango.EllipsizeMode.MIDDLE)

        self.row_new_filename = self.factory.create_actionrow(title=title, suffix=self.lblFilenameNew)
        listbox.append(self.row_new_filename)

        frame = Gtk.Frame()
        frame.set_margin_top(margin=0)
        frame.set_margin_end(margin=6)
        frame.set_margin_bottom(margin=6)
        frame.set_margin_start(margin=6)
        frame.set_child(listbox)
        self.append(frame)

    # Plugin tabs
    def __create_plugin_tabs(self):
        """Build one widget per registered tab and add it to the stack.

        A plugin whose factory raises is skipped with a log line: a broken tab
        must not stop the user from renaming a document.
        """
        registry = self.app.get_service('document-tabs')
        if registry is None:
            return
        for registration in registry.get_registrations():
            name = registration['name']
            try:
                widget = registration['factory'](self.app)
            except Exception as error:
                self.log.error(f"Document tab '{name}' could not be built: {error}")
                continue
            if widget is None:
                continue
            page = self.stack.add_titled(widget, name, registration['title'])
            if registration.get('icon_name'):
                page.set_icon_name(registration['icon_name'])
            self.plugin_tabs.append((name, widget))

        if self.plugin_tabs:
            self.switcher = Adw.ViewSwitcher()
            self.switcher.set_stack(self.stack)
            self.switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)

    def get_switcher(self):
        """The view switcher, or None when no plugin contributed a tab."""
        return self.switcher

    def _each_tab(self, method, *args):
        """Call a method on every plugin tab that implements it.

        Errors are logged and swallowed: whatever a plugin does here, renaming
        the document has to keep working.
        """
        for name, widget in self.plugin_tabs:
            handler = getattr(widget, method, None)
            if handler is None:
                continue
            try:
                yield name, handler(*args)
            except Exception as error:
                self.log.error(f"Document tab '{name}': {method} failed: {error}")

    def tabs_valid(self):
        """(True, None) when every tab accepts the rename, else (False, name)."""
        for name, valid in self._each_tab('is_valid'):
            if valid is False:
                return False, name
        return True, None

    def focus_tab(self, name):
        page = self.stack.get_child_by_name(name)
        if page is not None:
            self.stack.set_visible_child(page)

    def commit_tabs(self, old_id, new_id):
        """Write the tab edits, once the rename itself succeeded.

        Returns True when at least one tab reported that it changed something,
        so the caller can tell an empty apply from a real one.
        """
        changed = False
        for _name, result in self._each_tab('apply', old_id, new_id):
            changed = changed or bool(result)
        return changed

    def discard_tabs(self):
        for _name, _result in self._each_tab('discard'):
            pass

    @staticmethod
    def _success_or_error(widget, valid):
        widget.remove_css_class('warning')
        if valid:
            widget.remove_css_class('error')
            widget.add_css_class('success')
        else:
            widget.remove_css_class('success')
            widget.add_css_class('error')

    @staticmethod
    def _success_or_warning(widget, valid):
        if valid:
            widget.remove_css_class('warning')
            widget.remove_css_class('error')
            widget.add_css_class('success')
        else:
            widget.remove_css_class('error')
            widget.remove_css_class('success')
            widget.add_css_class('warning')

    @staticmethod
    def _dropdown_get_id(dropdown):
        item = dropdown.get_selected_item()
        return item.id if item is not None else 'Any'

    def _on_changed_entry(self, *args):
        try:
            adate = self.entry_date.get_text()
            acountry = self._dropdown_get_id(self.dpdCountry)
            agroup = self._dropdown_get_id(self.dpdGroup)
            asentby = self._dropdown_get_id(self.dpdSentBy)
            apurpose = self._dropdown_get_id(self.dpdPurpose)
            aconcept = self.util.valid_key(self.entry_concept.get_text().upper())
            asentto = self._dropdown_get_id(self.dpdSentTo)
            aextension = self.lblExt.get_text()

            self.result = f"{adate}-{acountry}-{agroup}-{asentby}-{apurpose}-{aconcept}-{asentto}.{aextension}"
            # The result is a plain filename, not markup. set_markup would parse
            # '&', '<' and '>' (common in AI-suggested values) and raise, which
            # left the preview stale.
            self.lblFilenameNew.set_text(self.result)
            self.lblFilenameNew.set_tooltip_text(self.result)

            v_date = self.validate_date(adate)
            v_group = self._cfg_group.exists_used(agroup)
            v_cty = self._cfg_country.exists_used(acountry)
            v_sentby = self._cfg_sentby.exists_used(asentby)
            v_purp = self._cfg_purpose.exists_used(apurpose)
            v_cnpt = len(aconcept) > 0
            v_sentto = self._cfg_sentto.exists_used(asentto)

            self._success_or_error(self.rowDate, v_date)
            self._success_or_error(self.rowCountry, v_cty)
            self._success_or_warning(self.rowGroup, v_group)
            self._success_or_error(self.rowSentBy, v_sentby)
            self._success_or_warning(self.rowPurpose, v_purp)
            self._success_or_error(self.rowConcept, v_cnpt)
            self._success_or_error(self.rowSentTo, v_sentto)
        except Exception as error:
            # Never re-raise from the live-preview handler: it is driven by
            # signals and by the AI suggestion flow, and a crash here left the
            # dialog broken and the preview frozen.
            self.log.error(error)
            self.result = ''
        # Outside the try: a failed preview is still a change, and the Rename
        # button has to go insensitive rather than stay on a stale verdict.
        self.emit('fields-changed')

    # Inline "+ Add" for restricted-vocabulary rows
    def _on_inline_add_value(self, _button, item_type, conf_obj):
        i_title = _(item_type.__title__)
        parent = self.get_root()
        helper = MiAZDialogAdd(self.app)
        title = _('Add {title}').format(title=i_title.lower())
        key1 = _('{title} key').format(title=i_title.title())
        key2 = _('Description')
        dialog = helper.create(parent=parent, title=title, key1=key1, key2=key2, action_label=_('Add'))
        dialog.connect('response', self._on_inline_add_response,
                       helper, item_type, conf_obj)
        dialog.present(parent)

    def _on_inline_add_response(self, _dialog, response, helper, item_type, conf_obj):
        if response != 'apply':
            return
        # Sanitize the key: strip characters not valid in a filename field.
        key = self.util.valid_key(helper.get_value1()).upper()
        value = helper.get_value2().strip()
        if not key or not value:
            return
        conf_obj.add_available(key, value)
        conf_obj.add_used(key, value)
        # Re-populate is triggered automatically by the 'used-updated' signal
        # (connected in __init__). It just needs to select the new value.
        self._select_value(item_type, key)
        self._on_changed_entry()

    def _select_value(self, item_type, key):
        dropdown = self.dropdown.get(item_type.__gtype_name__)
        if dropdown is None:
            return
        model = dropdown.get_model()
        for n, item in enumerate(model):
            if item.id == key:
                dropdown.set_selected(n)
                return

    # Concept autocomplete
    @staticmethod
    def _concept_factory_setup(_factory, list_item):
        label = Gtk.Label(xalign=0.0)
        label.set_margin_start(6)
        label.set_margin_end(6)
        list_item.set_child(label)

    @staticmethod
    def _concept_factory_bind(_factory, list_item):
        label = list_item.get_child()
        item = list_item.get_item()
        label.set_label(item.title if item is not None else '')

    def _set_concept_text(self, text):
        """Set the concept entry without opening the autocomplete popover.

        set_text() emits 'changed' synchronously, so _concept_loading is read
        before this returns. Used for programmatic fills (window opening, or
        reusing an existing concept) so completions appear only while typing.
        """
        self._concept_loading = True
        if self._concept_throttle_id:
            GLib.source_remove(self._concept_throttle_id)
            self._concept_throttle_id = 0
        self.entry_concept.set_text(text)
        self._concept_loading = False

    def _on_concept_entry_changed(self, entry):
        # Only react to keystrokes typed by the user, not programmatic fills.
        if self._concept_loading:
            return
        if self._concept_throttle_id:
            GLib.source_remove(self._concept_throttle_id)
        self._concept_throttle_id = GLib.timeout_add(
            150, self._refilter_concepts, entry.get_text())

    def _refilter_concepts(self, query):
        self._concept_throttle_id = 0
        self._concept_list_store.remove_all()
        query_u = (query or '').strip().upper()
        if not query_u:
            self._concept_popover.popdown()
            return False
        try:
            vocab = list(ENV['CACHE']['CONCEPTS']['ACTIVE'])
        except Exception:
            vocab = []
        # Show every concept from existing documents that contains the typed text.
        for concept in vocab:
            if query_u in concept.upper():
                self._concept_list_store.append(Concept(id=concept, title=concept))
        if self._concept_list_store.get_n_items() > 0:
            self._concept_popover.popup()
        else:
            self._concept_popover.popdown()
        return False

    def _on_concept_picked(self, _view, position):
        item = self._concept_list_store.get_item(position)
        if item is None:
            return
        self._set_concept_text(item.title)
        self._concept_popover.popdown()

    def _on_concept_key_pressed(self, _ctrl, keyval, _keycode, _state):
        if self._concept_popover.get_visible():
            if keyval == Gdk.KEY_Escape:
                self._concept_popover.popdown()
                return True
            if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
                pos = self._concept_selection.get_selected()
                if pos != Gtk.INVALID_LIST_POSITION:
                    self._on_concept_picked(self._concept_list_view, pos)
                else:
                    self._concept_popover.popdown()
                return True
        return False

    def _on_concept_focus_leave(self, _ctrl):
        # Defer so that clicks landing on a popover row register first.
        GLib.timeout_add(120, self._popdown_concept_popover)

    def _popdown_concept_popover(self):
        self._concept_popover.popdown()
        return False

    def validate_date(self, sdate: str) -> bool:
        if sdate == self._last_date_str:
            return self._last_date_valid
        try:
            adate = datetime.strptime(sdate, '%Y%m%d')
            iso8601 = f"{sdate}T00:00:00Z"
            self.calendar.select_day(GLib.DateTime.new_from_iso8601(iso8601))
            self.label_date.set_markup(adate.strftime("%A, %B %d %Y"))
            self._last_date_str = sdate
            self._last_date_valid = True
            return True
        except Exception:
            self._last_date_str = sdate
            self._last_date_valid = False
            return False

    def get_filepath_source(self) -> str:
        return self.filepath

    def get_filepath_target(self) -> str:
        return self.result

    def name_changes(self) -> bool:
        """True when applying would really rename the file.

        A document can be opened here only to edit what a plugin tab holds, with
        every filename field left alone. In that case there is nothing to rename
        and the tab edits still have to be written, so the caller needs to tell
        the two situations apart. The target is compared after the same
        uppercasing filename_rename applies.
        """
        return self.util.filename_rename_needed(
            os.path.basename(self.get_filepath_source()),
            os.path.basename(self.get_filepath_target()))

    def on_rename_cancel(self, *args):
        self.log.info("Rename canceled by user")

    def _on_document_display(self, *args):
        doc = self.get_filepath_source()
        self.actions.document_display(doc)

    def on_answer_question_delete(self, dialog, response):
        filepath = self.get_filepath_source()
        if response == 'apply':
            # Through the util service, not os.unlink: it emits
            # 'filename-deleted', which is how the index and the workspace
            # learn the document is gone. Deleting it here directly left both
            # holding an entry until the next full re-scan.
            self.util.filename_delete({filepath})
        else:
            self.actions.show_stack_page_by_name('workspace')
