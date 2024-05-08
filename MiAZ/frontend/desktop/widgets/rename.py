#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: rename.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Rename widget for single items
"""

import os
import sys
from datetime import datetime
from abc import abstractmethod
from gettext import gettext as _

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository.GdkPixbuf import Pixbuf

from MiAZ.backend.log import get_logger
from MiAZ.frontend.desktop.widgets.dialogs import MiAZDialogAdd
from MiAZ.backend.models import Group, Person, Country, Purpose, Concept, SentBy, SentTo
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries, MiAZGroups, MiAZPeople, MiAZPurposes, MiAZPeopleSentBy, MiAZPeopleSentTo


class MiAZRenameDialog(Gtk.Box):
    result = ''
    new_values = []
    dropdown = {}

    def __init__(self, app) -> Gtk.Widget:
        super(MiAZRenameDialog, self).__init__(orientation=Gtk.Orientation.VERTICAL, spacing=3, hexpand=True, vexpand=True)
        self.app = app
        self.backend = self.app.get_service('backend')
        self.factory = self.app.get_service('factory')
        self.actions = self.app.get_service('actions')
        self.icons = self.app.get_service('icons')
        self.config = self.backend.get_conf()
        self.util = self.app.get_service('util')
        self.log = get_logger('MiazRenameDialog')

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

        self.btnAccept = self.factory.create_button(icon_name='miaz-ok', title=_('Rename'), callback=self.on_rename_accept, css_classes=['opaque'])
        self.btnAccept.set_sensitive(True)
        # ~ self.btnAccept.get_style_context ().add_class('suggested-action')

        self.btnAccept.set_can_focus(True)
        self.btnAccept.set_focusable(True)
        self.btnAccept.set_receives_default(True)
        self.btnCancel = self.factory.create_button(icon_name='miaz-cancel', title=_('Cancel'), callback=self.on_rename_cancel)
        # ~ self.btnCancel.get_style_context ().add_class ('destructive-action')
        self.btnPreview = self.factory.create_button('miaz-preview', _('Preview'))
        self.btnPreview.connect('clicked', self._on_document_display)
        boxButtons = Gtk.CenterBox(hexpand=True)
        boxButtons.set_start_widget(self.btnCancel)
        boxButtons.set_center_widget(self.btnPreview)
        boxButtons.set_end_widget(self.btnAccept)
        boxButtons.set_margin_top(margin=12)
        boxButtons.set_margin_end(margin=12)
        boxButtons.set_margin_bottom(margin=12)
        boxButtons.set_margin_start(margin=12)
        self.append(boxButtons)

        self.config['Country'].connect('used-updated', self.update_dropdown, Country)
        self.config['Group'].connect('used-updated', self.update_dropdown, Group)
        self.config['SentBy'].connect('used-updated', self.update_dropdown, SentBy)
        self.config['Purpose'].connect('used-updated', self.update_dropdown, Purpose)
        self.config['SentTo'].connect('used-updated', self.update_dropdown, SentTo)
        self.backend.connect('repository-switched', self._update_dropdowns)

    def _update_dropdowns(self, *args):
        for item_type in [Country, Group, SentBy, Purpose, SentTo]:
            i_type = item_type.__gtype_name__
            i_title = _(item_type.__title__)
            config = self.config[i_type]
            self.actions.dropdown_populate(config, self.dropdown[i_type], item_type, False, False)

    def update_dropdown(self, config, item_type):
        title = item_type.__gtype_name__
        self.actions.dropdown_populate(config, self.dropdown[title], item_type)

    def set_data(self, doc):
        self.doc = doc
        self.filepath = doc
        name, self.extension = self.util.filename_details(doc)
        # ~ self.extension = filepath[filepath.rfind('.')+1:]
        # ~ self.doc = os.path.basename(filepath)
        self.suggested = self.util.get_fields(self.doc)
        if len(self.suggested[0]) == 0:
            adate = self.util.filename_get_creation_date(doc)
            self.entry_date.set_text(adate.strftime("%Y%m%d"))
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

    def __create_actionrow(self, title, item_type, conf) -> Gtk.Widget:
        icon_name = 'miaz-res-%s' % title.lower().replace(' ', '')
        icon = self.icons.get_image_by_name(name=icon_name)
        boxValue = self.__create_box_value()
        button = self.factory.create_button('miaz-res-manage', '')
        dropdown = self.factory.create_dropdown_generic(item_type, ellipsize=False) #, item)
        self.actions.dropdown_populate(conf, dropdown, item_type)
        boxValue.append(dropdown)
        boxValue.append(button)
        row = self.factory.create_actionrow(title, prefix=icon, suffix=boxValue)
        self.boxMain.append(row)
        return row, button, dropdown

    def _set_suggestion(self, dropdown, suggestion):
        found = False
        if len(suggestion) > 0:
            model = dropdown.get_model()
            n = 0
            for item in model:
                if item.id == suggestion:
                    dropdown.set_selected(n)
                    found = True
                n += 1
        if not found:
            dropdown.set_selected(0)

    def __create_field_0_date(self):
        """Field 0. Date"""
        title = _('Date')
        icon_name = 'miaz-res-date'
        icon = self.icons.get_image_by_name(name=icon_name)
        boxValue = self.__create_box_value()
        boxValue.set_hexpand(False)
        boxValue.set_valign(Gtk.Align.CENTER)
        self.rowDate = self.factory.create_actionrow(title=title, suffix=boxValue)
        self.boxMain.append(self.rowDate)
        self.calendar = Gtk.Calendar()
        self.calendar.connect('day-selected', self.calendar_day_selected)
        button_content = self.factory.create_button_content(icon_name='miaz-res-date', css_classes=['flat'])
        button = Gtk.MenuButton(child=button_content)
        popover = Gtk.Popover()
        popover.set_child(self.calendar)
        popover.present()
        button.set_popover(popover)
        self.label_date = Gtk.Label()
        self.label_date.get_style_context().add_class(class_name='caption')
        self.entry_date = Gtk.Entry()
        self.entry_date.set_max_length(8)
        self.entry_date.set_max_width_chars(8)
        self.entry_date.set_width_chars(8)
        self.entry_date.set_placeholder_text(_('YYYYmmdd'))
        self.entry_date.set_alignment(1.0)
        boxValue.append(self.label_date)
        boxValue.append(self.entry_date)
        boxValue.append(button)
        self.entry_date.connect('changed', self._on_changed_entry)

    def calendar_day_selected(self, calendar):
        adate = calendar.get_date()
        y = "%04d" % adate.get_year()
        m = "%02d" % adate.get_month()
        d = "%02d" % adate.get_day_of_month()
        self.entry_date.set_text("%s%s%s" % (y, m, d))

    def __create_field_1_country(self):
        self.rowCountry, self.btnCountry, self.dpdCountry = self.__create_actionrow(Country.__title__, Country, 'countries')
        self.dropdown['Country'] = self.dpdCountry
        self.btnCountry.connect('clicked', self.actions.manage_resource, MiAZCountries(self.app))
        self.dpdCountry.connect("notify::selected-item", self._on_changed_entry)

    def __create_field_2_group(self):
        self.rowGroup, self.btnGroup, self.dpdGroup = self.__create_actionrow(Group.__title__, Group, 'groups')
        self.dropdown['Group'] = self.dpdGroup
        self.btnGroup.connect('clicked', self.actions.manage_resource, MiAZGroups(self.app))
        self.dpdGroup.connect("notify::selected-item", self._on_changed_entry)

    def __create_field_4_sentby(self):
        self.rowSentBy, self.btnSentBy, self.dpdSentBy = self.__create_actionrow(SentBy.__title__, SentBy, 'Sentby')
        self.dropdown['SentBy'] = self.dpdSentBy
        self.btnSentBy.connect('clicked', self.actions.manage_resource, MiAZPeopleSentBy(self.app))
        self.dpdSentBy.connect("notify::selected-item", self._on_changed_entry)

    def __create_field_5_purpose(self):
        self.rowPurpose, self.btnPurpose, self.dpdPurpose = self.__create_actionrow(Purpose.__title__, Purpose, 'purposes')
        self.btnPurpose.connect('clicked', self.actions.manage_resource, MiAZPurposes(self.app))
        self.dropdown['Purpose'] = self.dpdPurpose
        self.dpdPurpose.connect("notify::selected-item", self._on_changed_entry)

    def __create_field_6_concept(self):
        """Field 0. Date"""
        title = Concept.__title__
        icon_name = 'miaz-res-concept'
        icon = self.icons.get_image_by_name(name=icon_name)
        boxValue = self.__create_box_value()
        self.rowConcept = self.factory.create_actionrow(title=title, suffix= boxValue)
        self.boxMain.append(self.rowConcept)
        button = self.factory.create_button('', '', css_classes=['flat'])
        button.set_sensitive(False)
        button.set_has_frame(False)
        self.entry_concept = Gtk.Entry()
        self.entry_concept.set_width_chars(41)
        self.entry_concept.set_alignment(1.0)
        self.entry_concept.set_placeholder_text(_('Type anything here...'))
        boxValue.append(self.entry_concept)
        boxValue.append(button)
        self.entry_concept.connect('changed', self._on_changed_entry)

    def __create_field_7_sentto(self):
        self.rowSentTo, self.btnSentTo, self.dpdSentTo = self.__create_actionrow(SentTo.__title__, SentTo, 'SentTo')
        self.dropdown['SentTo'] = self.dpdSentTo
        self.btnSentTo.connect('clicked', self.actions.manage_resource, MiAZPeopleSentTo(self.app))
        self.dpdSentTo.connect("notify::selected-item", self._on_changed_entry)

    def __create_field_8_extension(self):
        """Field 7. extension"""

        title = _('Extension')
        icon_name = 'miaz-res-extension'
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
        boxValueCur = self.__create_box_value()
        self.lblFilenameCur = Gtk.Label()
        self.lblFilenameCur.get_style_context().add_class(class_name='monospace')
        self.row_cur_filename = self.factory.create_actionrow(title=title, suffix=self.lblFilenameCur)
        self.boxMain.append(self.row_cur_filename)

        # New filename
        title = _('<b>New filename</b>')
        boxValueNew = self.__create_box_value()
        self.lblFilenameNew = Gtk.Label()
        self.lblFilenameNew.get_style_context().add_class(class_name='monospace')
        self.row_new_filename = self.factory.create_actionrow(title=title, suffix=self.lblFilenameNew)
        self.boxMain.append(self.row_new_filename)

    def _on_changed_entry(self, *args):
        def success_or_error(widget, valid):
            if valid:
                widget.get_style_context().remove_class(class_name='warning')
                widget.get_style_context().remove_class(class_name='error')
                widget.get_style_context().add_class(class_name='success')
            else:
                widget.get_style_context().remove_class(class_name='warning')
                widget.get_style_context().remove_class(class_name='success')
                widget.get_style_context().add_class(class_name='error')

        def success_or_warning(widget, valid):
            if valid:
                widget.get_style_context().remove_class(class_name='warning')
                widget.get_style_context().remove_class(class_name='error')
                widget.get_style_context().add_class(class_name='success')
            else:
                widget.get_style_context().remove_class(class_name='error')
                widget.get_style_context().remove_class(class_name='success')
                widget.get_style_context().add_class(class_name='warning')

        def dropdown_get_selected_item(dropdown):
            try:
                item = dropdown.get_selected_item().id
            except AttributeError:
                item = 'Any'
            return item

        try:
            fields = []
            adate = self.entry_date.get_text()
            acountry = dropdown_get_selected_item(self.dpdCountry)
            agroup = dropdown_get_selected_item(self.dpdGroup)
            asentby = dropdown_get_selected_item(self.dpdSentBy)
            apurpose = dropdown_get_selected_item(self.dpdPurpose)
            aconcept = self.util.valid_key(self.entry_concept.get_text().upper())
            asentto = dropdown_get_selected_item(self.dpdSentTo)
            aextension = self.lblExt.get_text()
            fields.append(adate)        # 0. Date
            fields.append(acountry)     # 1. Country
            fields.append(agroup)       # 2. Group
            fields.append(asentby)       # 4. SentBy
            fields.append(apurpose)     # 5. Purpose
            fields.append(aconcept)     # 6. Concept
            fields.append(asentto)       # 7. SentTo
            self.result = "%s.%s" % ('-'.join(fields), aextension)
            self.lblFilenameNew.set_markup(self.result)

            sentby = self.app.get_config('SentBy')
            sentto = self.app.get_config('SentTo')
            countries = self.app.get_config('Country')
            groups = self.app.get_config('Group')
            purposes = self.app.get_config('Purpose')
            v_date = self.validate_date(adate)
            v_group = groups.exists_used(agroup)
            v_cty = countries.exists_used(acountry)
            v_sentby = sentby.exists_used(asentby)
            v_purp = purposes.exists_used(apurpose)
            v_cnpt = len(aconcept) > 0
            v_sentto = sentto.exists_used(asentto)

            if v_group:
                success_or_warning(self.rowGroup, groups.exists_used(agroup))
            else:
                success_or_error(self.rowGroup, v_group)

            if v_purp:
                success_or_warning(self.rowPurpose, purposes.exists_used(apurpose))
            else:
                success_or_error(self.rowPurpose, v_purp)

            success_or_error(self.rowDate, v_date)
            success_or_error(self.rowCountry, v_cty)
            success_or_error(self.rowSentBy, v_sentby)
            success_or_error(self.rowConcept, v_cnpt)
            success_or_error(self.rowSentTo, v_sentto)
        except Exception as error:
            self.log.error(error)
            self.result = ''
            raise

    def validate_date(self, sdate: str) -> bool:
        try:
            adate = datetime.strptime(sdate, '%Y%m%d')
            iso8601 = "%sT00:00:00Z" % sdate
            self.calendar.select_day(GLib.DateTime.new_from_iso8601(iso8601))
            self.label_date.set_markup(adate.strftime("%A, %B %d %Y"))
            return True
        except Exception as error:
            return False

    def get_filepath_source(self) -> str:
        return self.filepath

    def get_filepath_target(self) -> str:
        return self.result

    def on_rename_accept(self, *args):
        body = _('<big>You are about to set this new filename:</big>\n\n<b>%s</b>') % self.get_filepath_target()
        widget = Gtk.Label()
        widget.set_markup(body)
        question = self.factory.create_dialog_question(self.app.win, _('Are you sure?'), widget)
        question.connect('response', self.on_answer_question_rename)
        question.show()

    def on_answer_question_rename(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            source = self.get_filepath_source()
            target = self.get_filepath_target()
            self.util.filename_rename(source, target)
            dialog.destroy()
            self.app.show_stack_page_by_name('workspace')
        else:
            dialog.destroy()

    def on_rename_cancel(self, *args):
        self.app.show_stack_page_by_name('workspace')

    def _on_document_display(self, *args):
        doc = self.get_filepath_source()
        self.actions.document_display(doc)

    def on_document_delete(self, button, filepath):
        body = _('<big>You are about to delete the following document:\n\n<b>%s</b>\n\nConfirm, please.</big>') % os.path.basename(filepath)
        widget = Gtk.Label()
        widget.set_markup(body)
        question = self.factory.create_dialog_question(self, _('Are you sure?'), widget)
        question.connect('response', self.on_answer_question_delete)
        question.show()

    def on_answer_question_delete(self, dialog, response):
        filepath = self.get_filepath_source()
        if response == Gtk.ResponseType.YES:
            try:
                os.unlink(filepath)
                self.log.debug("Document deleted: %s", filepath)
                dialog.destroy()
                self.destroy()
            except FileNotFoundError as error:
                self.log.error("Something went wrong: %s", error)
                self.log.error("Doesn't it exist? Really?")
        else:
            self.app.show_stack_page_by_name('workspace')
