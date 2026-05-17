#!/usr/bin/python3
# File: rename.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Rename widget for single items

import difflib
import os
from datetime import datetime
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import Pango

from MiAZ.env import ENV
from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import Group, Country, Purpose, Concept, SentBy, SentTo
from MiAZ.frontend.desktop.services.dialogs import MiAZDialogAdd
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries, MiAZGroups, MiAZPurposes, MiAZPeopleSentBy, MiAZPeopleSentTo
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewConcept


class MiAZRenameDialog(Gtk.Box):
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
        self.__create_field_9_result() # Result filename

        frmMain = Gtk.Frame()
        frmMain.set_margin_top(margin=6)
        frmMain.set_margin_end(margin=6)
        frmMain.set_margin_bottom(margin=6)
        frmMain.set_margin_start(margin=6)
        frmMain.set_child(self.boxMain)
        self.append(frmMain)

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

    def update_dropdown(self, config, item_type):
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
            self.entry_concept.set_text(self.suggested[5])
        self._set_suggestion(self.dpdSentTo, self.suggested[6])
        self.lblExt.set_text(self.extension)
        self.lblFilenameCur.set_markup(os.path.basename(self.doc))
        self.lblFilenameCur.set_selectable(True)
        self.lblFilenameNew.set_markup(self.result)
        self.lblFilenameNew.set_selectable(True)
        self._on_changed_entry()

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
                    self.entry_concept.set_text(item.title)
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
        self.label_date.get_style_context().add_class(class_name='caption')
        self.entry_date = Gtk.Entry()
        self.entry_date.set_visible(False)
        self.entry_date.set_max_length(8)
        self.entry_date.set_max_width_chars(8)
        self.entry_date.set_width_chars(8)
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
        self._concept_suppress_next = False
        self.entry_concept.connect('changed', self._on_concept_entry_changed)
        self.entry_concept.connect('changed', self._on_changed_entry)

        # Escape closes the popover.
        key_ctrl = Gtk.EventControllerKey()
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

    def __create_field_9_result(self, *args):
        """Field 7. extension"""
        # Current filename
        title = _('Current filename')
        self.lblFilenameCur = Gtk.Label()
        self.lblFilenameCur.get_style_context().add_class(class_name='monospace')
        self.lblFilenameCur.get_style_context().add_class(class_name='error')
        self.row_cur_filename = self.factory.create_actionrow(title=title, suffix=self.lblFilenameCur)
        self.boxMain.append(self.row_cur_filename)
        self.lblFilenameCur.set_ellipsize(True)
        self.lblFilenameCur.set_property('ellipsize', Pango.EllipsizeMode.MIDDLE)

        # New filename
        title = _('<b>New filename</b>')
        self.lblFilenameNew = Gtk.Label()
        self.lblFilenameNew.get_style_context().add_class(class_name='monospace')
        self.lblFilenameNew.get_style_context().add_class(class_name='success')
        self.lblFilenameNew.set_ellipsize(True)
        self.lblFilenameNew.set_property('ellipsize', Pango.EllipsizeMode.MIDDLE)

        self.row_new_filename = self.factory.create_actionrow(title=title, suffix=self.lblFilenameNew)
        self.boxMain.append(self.row_new_filename)

    @staticmethod
    def _success_or_error(widget, valid):
        ctx = widget.get_style_context()
        ctx.remove_class('warning')
        if valid:
            ctx.remove_class('error')
            ctx.add_class('success')
        else:
            ctx.remove_class('success')
            ctx.add_class('error')

    @staticmethod
    def _success_or_warning(widget, valid):
        ctx = widget.get_style_context()
        if valid:
            ctx.remove_class('warning')
            ctx.remove_class('error')
            ctx.add_class('success')
        else:
            ctx.remove_class('error')
            ctx.remove_class('success')
            ctx.add_class('warning')

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
            self.lblFilenameNew.set_markup(self.result)
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
            self.log.error(error)
            self.result = ''
            raise

    # ------------------------------------------------------------------
    # Inline "+ Add" for restricted-vocabulary rows
    # ------------------------------------------------------------------

    def _on_inline_add_value(self, _button, item_type, conf_obj):
        i_title = _(item_type.__title__)
        parent = self.get_root()
        helper = MiAZDialogAdd(self.app)
        title = _('<b>Add new {title}</b>').format(title=i_title.lower())
        key1 = _('<b>{title} key</b>').format(title=i_title.title())
        key2 = _('<b>Description</b>')
        dialog = helper.create(parent=parent, title=title, key1=key1, key2=key2)
        dialog.connect('response', self._on_inline_add_response,
                       helper, item_type, conf_obj)
        dialog.present(parent)

    def _on_inline_add_response(self, _dialog, response, helper, item_type, conf_obj):
        if response != 'apply':
            return
        key = helper.get_value1().strip().upper()
        value = helper.get_value2().strip()
        if not key or not value:
            return
        conf_obj.add_available(key, value)
        conf_obj.add_used(key, value)
        # Re-populate is triggered automatically by the 'used-updated' signal
        # (connected in __init__) — we just need to select the new value.
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

    # ------------------------------------------------------------------
    # Concept autocomplete
    # ------------------------------------------------------------------

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

    def _on_concept_entry_changed(self, entry):
        if self._concept_throttle_id:
            GLib.source_remove(self._concept_throttle_id)
        self._concept_throttle_id = GLib.timeout_add(
            150, self._refilter_concepts, entry.get_text())

    def _refilter_concepts(self, query):
        self._concept_throttle_id = 0
        # If we just accepted a suggestion, the 'changed' signal we caused
        # by set_text(...) would otherwise re-open the popover on an exact
        # match. Swallow exactly one refresh after a pick.
        if self._concept_suppress_next:
            self._concept_suppress_next = False
            self._concept_popover.popdown()
            return False
        self._concept_list_store.remove_all()
        query_u = (query or '').strip().upper()
        if not query_u:
            self._concept_popover.popdown()
            return False
        try:
            vocab = list(ENV['CACHE']['CONCEPTS']['ACTIVE'])
        except Exception:
            vocab = []
        matches = difflib.get_close_matches(query_u, vocab, n=8, cutoff=0.4)
        for token in matches:
            self._concept_list_store.append(Concept(id=token, title=token))
        if self._concept_list_store.get_n_items() > 0:
            self._concept_popover.popup()
        else:
            self._concept_popover.popdown()
        return False

    def _on_concept_picked(self, _view, position):
        item = self._concept_list_store.get_item(position)
        if item is None:
            return
        self._concept_suppress_next = True
        self.entry_concept.set_text(item.title)
        self._concept_popover.popdown()

    def _on_concept_key_pressed(self, _ctrl, keyval, _keycode, _state):
        if keyval == Gdk.KEY_Escape and self._concept_popover.get_visible():
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

    def on_rename_cancel(self, *args):
        self.log.info("Rename canceled by user")

    def _on_document_display(self, *args):
        doc = self.get_filepath_source()
        self.actions.document_display(doc)

    def on_answer_question_delete(self, dialog, response):
        filepath = self.get_filepath_source()
        if response == 'apply':
            try:
                os.unlink(filepath)
                self.log.debug(f"Document deleted: {filepath}")
            except FileNotFoundError as error:
                self.log.error(f"Something went wrong: {error}")
                raise
        else:
            self.actions.show_stack_page_by_name('workspace')
