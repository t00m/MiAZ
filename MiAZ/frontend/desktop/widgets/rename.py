#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import shutil
from datetime import datetime
from abc import abstractmethod

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw
from gi.repository import Gio
from gi.repository import GLib
from gi.repository.GdkPixbuf import Pixbuf

from MiAZ.backend.log import get_logger
from MiAZ.frontend.desktop.widgets.dialogs import MiAZDialogAdd
from MiAZ.backend.models import File, Collection, Person, Country, Purpose, Concept

class MiAZRenameDialog(Gtk.Dialog):
    result = ''
    new_values = []

    def __init__(self, app, filepath: str, suggested: list) -> Gtk.Widget:
        super(MiAZRenameDialog, self).__init__()
        self.app = app
        self.backend = self.app.get_backend()
        self.factory = self.app.get_factory()
        self.actions = self.app.get_actions()
        self.log = get_logger('MiazRenameDialog')
        self.set_size_request(800, 600)
        self.set_transient_for(self.app.win)
        self.set_modal(True)

        # Basic data
        # ~ self.row = row
        self.filepath = filepath
        self.extension = filepath[filepath.rfind('.')+1:]
        self.suggested = suggested
        self.doc = os.path.basename(filepath)

        # Header & Butons
        self.btnAccept = self.factory.create_button('', 'rename', self.on_rename_accept)
        self.btnAccept.set_sensitive(False)
        self.btnAccept.get_style_context ().add_class ('suggested-action')
        self.btnAccept.set_can_focus(True)
        self.btnAccept.set_receives_default(True)
        btnCancel = self.factory.create_button('', 'cancel', self.on_rename_cancel)
        btnCancel.get_style_context ().add_class ('destructive-action')

        btnPreview = self.factory.create_button('', 'preview', self.on_document_display, data=self.filepath)
        # ~ btnFileDisplay.set_child(icon)
        # ~ btnFileDisplay.connect('clicked', self.on_document_display, self.filepath)
        # ~ btnFileDisplay.set_valign(Gtk.Align.CENTER)
        # ~ btnFileDisplay.set_hexpand(False)

        btnDelete = self.factory.create_button('', 'delete', self.on_document_delete, data=self.filepath)
        self.set_default_response(Gtk.ResponseType.ACCEPT)
        lblHeaderTitle = Gtk.Label()
        lblHeaderTitle.set_markup('<b>Rename file</b>')
        self.dlgHeader = Adw.HeaderBar()
        self.dlgHeader.set_show_end_title_buttons(False)
        self.dlgHeader.pack_start(btnDelete)
        self.dlgHeader.pack_end(self.btnAccept)
        self.dlgHeader.pack_end(btnCancel)
        self.dlgHeader.pack_end(btnPreview)
        self.dlgHeader.set_title_widget(lblHeaderTitle)
        self.set_titlebar(self.dlgHeader)

        # Contents
        self.contents = self.get_content_area()

        # Box to be inserted as contents
        self.boxMain = Gtk.ListBox.new() #orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.boxMain.set_vexpand(False)
        self.boxMain.set_hexpand(False)
        self.boxMain.set_margin_top(margin=12)
        self.boxMain.set_margin_end(margin=12)
        self.boxMain.set_margin_bottom(margin=12)
        self.boxMain.set_margin_start(margin=12)

        # Filename format: {timestamp}-{country}-{collection}-{from}-{purpose}-{concept}-{to}.{extension}
        self.__create_field_0_date() # Field 1. Country
        self.__create_field_1_country() # Field 3. From
        self.__create_field_2_collection() # Field 2. Collection
        self.__create_field_3_from() # Field 3. From
        self.__create_field_4_purpose() # Field 3. Purpose
        self.__create_field_5_concept() # Field 3. Concept
        self.__create_field_6_to() # Field 6. To
        self.__create_field_7_extension() # Field 7. Extension
        self.__create_field_8_result() # Result filename

        self.contents.append(self.boxMain)

        # Connect signals and verify
        # ~ self.entry_date.connect('changed', self.on_changed_entry)
        # ~ self.entry_country.connect('changed', self.on_changed_entry)
        # ~ self.entry_collection.connect('changed', self.on_changed_entry)
        # ~ self.entry_from.connect('changed', self.on_changed_entry)
        # ~ self.entry_purpose.connect('changed', self.on_changed_entry)
        # ~ self.entry_concept.connect('changed', self.on_changed_entry)
        # ~ self.entry_to.connect('changed', self.on_changed_entry)
        # ~ self.on_changed_entry()
        # ~ self.connect('response', self._on_response_rename)
        self.on_changed_entry()

    def __create_box_value(self) -> Gtk.Box:
        box = Gtk.Box.new(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.set_hexpand(False)
        box.set_valign(Gtk.Align.CENTER)
        return box

    def __create_actionrow(self, title, item_type, conf) -> Adw.ActionRow:
        row = Adw.ActionRow.new()
        row.set_title(title)
        row.set_icon_name('miaz-res-%s' % title.lower())
        boxValue = self.__create_box_value()
        row.add_suffix(boxValue)
        self.boxMain.append(row)
        button = self.factory.create_button('miaz-list-add', '')
        dropdown = self.factory.create_dropdown_generic(item_type) #, item)
        self.actions.dropdown_populate(dropdown, item_type, conf)
        boxValue.append(dropdown)
        boxValue.append(button)
        return row, button, dropdown

    def _set_suggestion(self, dropdown, suggestion):
        found = False
        if len(suggestion) > 0:
            model = dropdown.get_model()
            n = 0
            for item in model:
                # ~ self.log.debug("%s == %s? %s", item.id, suggestion, item.id == suggestion)
                if item.id == suggestion:
                    dropdown.set_selected(n)
                    found = True
                n += 1

        if not found:
            dropdown.set_selected(0)

    def __create_field_0_date(self):
        """Field 0. Date"""
        self.rowDate = Adw.ActionRow.new()
        self.rowDate.set_title('Date')
        self.rowDate.set_icon_name('miaz-res-date')
        boxValue = self.__create_box_value()
        boxValue.set_hexpand(False)
        boxValue.set_valign(Gtk.Align.CENTER)
        self.rowDate.add_suffix(boxValue)
        self.boxMain.append(self.rowDate)
        button = self.factory.create_button('miaz-res-date', '')
        self.entry_date = Gtk.Entry()
        self.entry_date.set_max_length(8)
        self.entry_date.set_max_width_chars(8)
        self.entry_date.set_width_chars(8)
        self.entry_date.set_placeholder_text('YYYYmmdd')
        self.entry_date.set_alignment(1.0)
        boxValue.append(self.entry_date)
        boxValue.append(button)

        if len(self.suggested[0]) > 0:
            self.entry_date.set_text(self.suggested[0])

        self.entry_date.connect('changed', self.on_changed_entry)

    def __create_field_1_country(self):
        self.rowCountry, self.btnCountry, self.dpdCountry = self.__create_actionrow('Country', Country, 'countries')
        self.btnCountry.set_sensitive(False)
        self.btnCountry.set_has_frame(False)
        self.btnCountry.set_child(None)
        self._set_suggestion(self.dpdCountry, self.suggested[1])
        self.dpdCountry.connect("notify::selected-item", self.on_changed_entry)

    def __create_field_2_collection(self):
        self.rowCollection, self.btnCollection, self.dpdCollection = self.__create_actionrow('Collection', Collection, 'collections')
        self._set_suggestion(self.dpdCollection, self.suggested[2])
        self.btnCollection.connect('clicked', self.on_collection_add)
        self.dpdCollection.connect("notify::selected-item", self.on_changed_entry)

    def __create_field_3_from(self):
        self.rowFrom, self.btnFrom, self.dpdFrom = self.__create_actionrow('From', Person, 'organizations')
        self.btnFrom.connect('clicked', self.on_organization_from_add)
        self._set_suggestion(self.dpdFrom, self.suggested[3])
        self.dpdFrom.connect("notify::selected-item", self.on_changed_entry)

    def __create_field_4_purpose(self):
        self.rowPurpose, self.btnPurpose, self.dpdPurpose = self.__create_actionrow('Purpose', Purpose, 'purposes')
        self._set_suggestion(self.dpdPurpose, self.suggested[4])
        self.dpdPurpose.connect("notify::selected-item", self.on_changed_entry)

    def __create_field_5_concept(self):
        """Field 0. Date"""
        self.rowConcept = Adw.ActionRow.new()
        self.rowConcept.set_title('Concept')
        self.rowConcept.set_icon_name('miaz-res-concept')
        boxValue = self.__create_box_value()
        self.rowConcept.add_suffix(boxValue)
        self.boxMain.append(self.rowConcept)
        button = self.factory.create_button('', '', css_classes=['flat'])
        button.set_sensitive(False)
        button.set_has_frame(False)
        self.entry_concept = Gtk.Entry()
        self.entry_concept.set_alignment(1.0)
        self.entry_concept.set_placeholder_text('Type anything here...')
        boxValue.append(self.entry_concept)
        boxValue.append(button)

        if len(self.suggested[5]) > 0:
            self.entry_concept.set_text(self.suggested[5])

        self.entry_concept.connect('changed', self.on_changed_entry)

    def __create_field_6_to(self):
        self.rowTo, self.btnTo, self.dpdTo = self.__create_actionrow('To', Person, 'organizations')
        self._set_suggestion(self.dpdTo, self.suggested[6])
        self.dpdTo.connect("notify::selected-item", self.on_changed_entry)

    def __create_field_7_extension(self):
        """Field 7. extension"""
        self.rowExt = Adw.ActionRow.new()
        self.rowExt.set_title('Extension')
        self.rowExt.set_icon_name('miaz-res-extension')
        boxValue = self.__create_box_value()
        self.rowExt.add_suffix(boxValue)
        self.boxMain.append(self.rowExt)
        button = self.factory.create_button('', '', css_classes=['flat'])
        button.set_sensitive(False)
        button.set_has_frame(False)
        self.lblExt = Gtk.Label()
        boxValue.append(self.lblExt)
        boxValue.append(button)
        self.lblExt.set_text(self.extension)

    def __create_field_8_result(self, *args):
        """Field 7. extension"""
        # Current filename
        self.row_cur_filename = Adw.ActionRow.new()
        self.row_cur_filename.set_title("Current filename")
        boxValueCur = self.__create_box_value()
        lblFilenameCur = Gtk.Label()
        lblFilenameCur.set_markup(self.doc)
        lblFilenameCur.set_selectable(True)
        self.row_cur_filename.add_suffix(lblFilenameCur)
        self.boxMain.append(self.row_cur_filename)

        # ~ icon = self.app.icman.get_icon_mimetype_from_file(self.filepath, 36, 36)
        # ~ icon.set_icon_size(Gtk.IconSize.INHERIT)
        # ~ boxFileDisplayButton = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        # ~ btnFileDisplay = button = Gtk.Button()
        # ~ btnFileDisplay.set_child(icon)
        # ~ btnFileDisplay.connect('clicked', self.on_document_display, self.filepath)
        # ~ btnFileDisplay.set_valign(Gtk.Align.CENTER)
        # ~ btnFileDisplay.set_hexpand(False)
        # ~ self.row_cur_filename.add_suffix(btnFileDisplay)

        self.row_new_filename = Adw.ActionRow.new()
        self.row_new_filename.set_title("<b>New filename</b>")
        boxValueNew = self.__create_box_value()
        self.lblFilenameNew = Gtk.Label()
        self.lblFilenameNew.set_markup(self.result)
        self.lblFilenameNew.set_selectable(True)
        self.row_new_filename.add_suffix(self.lblFilenameNew)
        self.boxMain.append(self.row_new_filename)

    def _on_response_rename(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            source = self.get_filepath_source()
            target = os.path.join(os.path.dirname(source), self.get_filepath_target())
            shutil.move(source, target)
            self.log.debug("Rename document from '%s' to '%s'", os.path.basename(source), os.path.basename(target))
            self.backend.check_source()
        self.destroy()

    def on_changed_entry(self, *args):
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

        try:
            fields = []
            adate = self.entry_date.get_text()
            acountry = self.dpdCountry.get_selected_item().id
            acollection = self.dpdCollection.get_selected_item().id
            afrom = self.dpdFrom.get_selected_item().id
            apurpose = self.dpdPurpose.get_selected_item().id
            aconcept = self.entry_concept.get_text().upper().replace(' ', '_')
            ato = self.dpdTo.get_selected_item().id
            aextension = self.lblExt.get_text()
            fields.append(adate) # 0. Date
            fields.append(acountry) # 1. Country
            fields.append(acollection) # 2. Collection
            fields.append(afrom) # 3. From
            fields.append(apurpose) # 4. Purpose
            fields.append(aconcept) # 5. Concept
            fields.append(ato) # 6. To
            self.result = "%s.%s" % ('-'.join(fields), aextension)
            self.lblFilenameNew.set_markup(self.result)

            organizations = self.app.get_config('organizations')
            countries = self.app.get_config('countries')
            collections = self.app.get_config('collections')
            purposes = self.app.get_config('purposes')
            v_date = self.validate_date(adate)
            v_col = len(acollection) > 0
            v_cty = countries.exists(acountry)
            v_from = organizations.exists(afrom)
            v_purp = len(apurpose) > 0
            v_cnpt = len(aconcept) > 0
            v_to = organizations.exists(ato)

            if v_col:
                success_or_warning(self.rowCollection, collections.exists(acollection))
            else:
                success_or_error(self.rowCollection, v_col)

            if v_purp:
                success_or_warning(self.rowPurpose, purposes.exists(apurpose))
            else:
                success_or_error(self.rowPurpose, v_purp)

            success_or_error(self.rowDate, v_date)
            success_or_error(self.rowCountry, v_cty)
            success_or_error(self.rowFrom, v_from)
            success_or_error(self.rowConcept, v_cnpt)
            success_or_error(self.rowTo, v_to)

            if v_date and v_from and v_to and v_cty and v_col and v_purp and v_cnpt:
                self.btnAccept.set_sensitive(True)
            else:
                self.btnAccept.set_sensitive(False)
        except Exception as error:
            self.result = ''

    def validate_date(self, adate: str) -> bool:
        try:
            datetime.strptime(adate, '%Y%m%d')
            return True
        except:
            return False

    def validate(self, fields: list) -> None:
        valid_filename = False

        # Validate Collection:
        cnfCollections = self.app.get_config('collections')
        collections = cnfCollections.load()
        if not cnfCollections.exists(fields[2]):
            collections.append(fields[2])
            cnfCollections.save(collections)
            self.new_values.append(('collections', '', fields[2]))

        # Validate From:
        cnfOrgs = self.app.get_config('organizations')
        orgs = cnfOrgs.load()
        if not cnfOrgs.exists(fields[3]):
            cnfOrgs.set(fields[3], '')
            cnfOrgs.save(cnfOrgs)
            self.new_values.append(('From', '', fields[3]))

        # Validate To:
        cnfOrgs = self.app.get_config('organizations')
        orgs = cnfOrgs.load()
        if not cnfOrgs.exists(fields[3]):
            cnfOrgs.set(fields[3], '')
            cnfOrgs.save(cnfOrgs)
            self.new_values.append(('To', '', fields[6]))


    def get_filepath_source(self) -> str:
        return self.filepath

    def get_filepath_target(self) -> str:
        return self.result

    # ~ def get_row(self):
        # ~ return self.row

    def on_rename_accept(self, *args):
        body = "<big>You are about to rename:\n\n<b>%s</b>\n\nto\n\n<b>%s</b></big>" % (os.path.basename(self.get_filepath_source()), self.get_filepath_target())
        widget = Gtk.Label()
        widget.set_markup(body)
        question = self.factory.create_dialog_question(self, "Are you sure?", widget)
        question.connect('response', self.on_answer_question_rename)
        question.show()

    def on_answer_question_rename(self, dialog, response):
        if response == Gtk.ResponseType.YES:
            source = self.get_filepath_source()
            target = os.path.join(os.path.dirname(source), self.get_filepath_target())
            if source != target and not os.path.exists(target):
                shutil.move(source, target)
                dialog.destroy()
                self.destroy()
        else:
            dialog.destroy()

    def on_rename_cancel(self, *args):
        self.response(Gtk.ResponseType.CANCEL)
        self.destroy()

    def on_document_display(self, button, filepath):
        self.log.debug("Displaying %s", filepath)
        os.system("xdg-open '%s'" % filepath)

    def on_document_delete(self, button, filepath):
        body = "<big>You are about to delete the following document:\n\n<b>%s</b>\n\nConfirm, please.</big>" % os.path.basename(filepath)
        widget = Gtk.Label()
        widget.set_markup(body)
        question = self.factory.create_dialog_question(self, "Are you sure?", widget)
        question.connect('response', self.on_answer_question_delete)
        question.show()

    def on_organizations_refresh(self, *args):
        config = self.app.get_config('organizations')
        organizations = config.load()
        model = self.combobox_from.get_model()
        model.clear()
        for alias in organizations:
            model.append([alias, "<i>%s</i>" % organizations[alias]])

        model = self.combobox_to.get_model()
        model.clear()
        for alias in organizations:
            model.append([alias, "<i>%s</i>" % organizations[alias]])


    def on_answer_question_delete(self, dialog, response):
        filepath = self.get_filepath_source()
        if response == Gtk.ResponseType.YES:
            try:
                os.unlink(filepath)
                self.log.debug("Document deleted: %s", filepath)
                # ~ self.response(Gtk.ResponseType.ACCEPT)
                dialog.destroy()
                self.destroy()
            except FileNotFoundError as error:
                self.log.error("Something went wrong: %s", error)
                self.log.error("Doesn't it exist? Really?")
        else:
            dialog.destroy()
            self.response(Gtk.ResponseType.CANCEL)

    def on_organization_from_add(self, *args):
        dialog = MiAZDialogAdd(self.app, self.get_root(), 'Add new person or entity', 'Initials', 'Full name')
        dialog.connect('response', self.on_response_organization_from_add)
        dialog.show()

    def on_collection_add(self, *args):
        dialog = MiAZDialogAdd(self.app, self.get_root(), 'Add new collection', 'Collection', '')
        boxKey2 = dialog.get_boxKey2()
        boxKey2.set_visible(False)
        dialog.connect('response', self.on_response_collection_add)
        dialog.show()

    def on_organization_to_add(self, *args):
        dialog = MiAZDialogAdd(self.app, self.get_root(), 'Add new person or entity', 'Initials', 'Full name')
        dialog.connect('response', self.on_response_organization_to_add)
        dialog.show()

    def on_response_organization_from_add(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            key = dialog.get_value1()
            value = dialog.get_value2()
            if len(key) > 0 and len(value) > 0:
                config = self.app.get_config('organizations')
                items = config.load()
                items[key.upper()] = value
                config.save(items)

                # Update dropdown
                self.actions.dropdown_populate(self.dpdFrom, Person, 'organizations')
                self.select_dropdown_item(self.dpdFrom, key)
        dialog.destroy()

    def select_dropdown_item(self, dropdown, key):
        found = False
        model = dropdown.get_model()
        n = 0
        for item in model:
            if item.id.upper() == key.upper():
                dropdown.set_selected(n)
                found = True
            n += 1
        if not found:
            dropdown.set_selected(0)

    def on_response_collection_add(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            key = dialog.get_value1()
            if len(key) > 0:
                config = self.app.get_config('collections')
                config.add(key)

                # ~ # Update combobox from
                # ~ model = self.combobox_from.get_model()
                # ~ treeiter = model.append([key.upper(), "<i>%s</i>" % value])
                # ~ self.combobox_from.set_active_iter(treeiter)
        dialog.destroy()

    def on_response_organization_to_add(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            key = dialog.get_value1()
            value = dialog.get_value2()
            if len(key) > 0 and len(value) > 0:
                config = self.app.get_config('organizations')
                items = config.load()
                items[key.upper()] = value
                config.save(items)

                # Update combobox from
                model = self.combobox_to.get_model()
                treeiter = model.append([key.upper(), "<i>%s</i>" % value])
                self.combobox_to.set_active_iter(treeiter)
        dialog.destroy()
