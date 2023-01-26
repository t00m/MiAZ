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
from MiAZ.backend.models import File, Group, Subgroup, Person, Country, Purpose, Concept
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries, MiAZGroups, MiAZPeople, MiAZPurposes, MiAZSubgroups


class MiAZRenameDialog(Gtk.Box):
    result = ''
    new_values = []
    dropdowns = []

    def __init__(self, app) -> Gtk.Widget:
        super(MiAZRenameDialog, self).__init__(orientation=Gtk.Orientation.VERTICAL, spacing=3, hexpand=True, vexpand=True)
        self.app = app
        self.backend = self.app.get_backend()
        self.factory = self.app.get_factory()
        self.actions = self.app.get_actions()
        self.config = self.backend.get_conf()
        self.log = get_logger('MiazRenameDialog')
        # ~ self.set_size_request(800, 600)
        # ~ self.set_transient_for(self.app.win)
        # ~ self.set_modal(True)

        # Basic data
        # ~ self.row = row


        # Header & Butons


        # ~ self.btnDelete = self.factory.create_button('', 'delete', self.on_document_delete, data=self.filepath)
        # ~ self.set_default_response(Gtk.ResponseType.ACCEPT)
        # ~ lblHeaderTitle = Gtk.Label()
        # ~ lblHeaderTitle.set_markup('<b>Rename file</b>')
        # ~ self.dlgHeader = Adw.HeaderBar()
        # ~ self.dlgHeader.set_show_end_title_buttons(False)
        # ~ self.dlgHeader.pack_start(self.btnDelete)
        # ~ self.dlgHeader.pack_end(self.btnAccept)
        # ~ self.dlgHeader.pack_end(self.btnCancel)
        # ~ self.dlgHeader.pack_end(self.btnPreview)
        # ~ self.dlgHeader.set_title_widget(lblHeaderTitle)
        # ~ self.set_titlebar(self.dlgHeader)

        # Contents
        # ~ self.contents = self.get_content_area()

        # Box to be inserted as contents
        self.boxMain = Gtk.ListBox.new() #orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.boxMain.set_vexpand(True)
        self.boxMain.set_hexpand(True)

        # Filename format: {timestamp}-{country}-{group}-{subgroup}-{from}-{purpose}-{concept}-{to}.{extension}
        self.__create_field_0_date() # Field 0. Date
        self.__create_field_1_country() # Field 1. Country
        self.__create_field_2_group() # Field 2. Group
        self.__create_field_3_subgroup() # Field 2. Subgroup
        self.__create_field_4_sentby() # Field 4. Sent by
        self.__create_field_5_purpose() # Field 5. Purpose
        self.__create_field_6_concept() # Field 6. Concept
        self.__create_field_7_sentto() # Field 7. Sent to
        self.__create_field_8_extension() # Field 8. Extension
        self.__create_field_9_result() # Result filename

        frmMain = Gtk.Frame()
        frmMain.set_margin_top(margin=12)
        frmMain.set_margin_end(margin=12)
        frmMain.set_margin_bottom(margin=12)
        frmMain.set_margin_start(margin=12)
        frmMain.set_child(self.boxMain)
        self.append(frmMain)

        self.btnAccept = self.factory.create_button('miaz-ok', 'rename', self.on_rename_accept, css_classes=['opaque'])
        self.btnAccept.set_sensitive(False)
        # ~ self.btnAccept.get_style_context ().add_class('suggested-action')
        self.btnAccept.set_can_focus(True)
        self.btnAccept.set_receives_default(True)
        self.btnCancel = self.factory.create_button('miaz-cancel', 'cancel', self.on_rename_cancel)
        # ~ self.btnCancel.get_style_context ().add_class ('destructive-action')
        self.btnPreview = self.factory.create_button('miaz-preview', 'preview')
        boxButtons = Gtk.CenterBox(hexpand=True)
        boxButtons.set_start_widget(self.btnCancel)
        boxButtons.set_center_widget(self.btnPreview)
        boxButtons.set_end_widget(self.btnAccept)
        boxButtons.set_margin_top(margin=12)
        boxButtons.set_margin_end(margin=12)
        boxButtons.set_margin_bottom(margin=12)
        boxButtons.set_margin_start(margin=12)
        self.append(boxButtons)

    def update_dropdowns(self):
        for dropdown, item_type in self.dropdowns:
            self.actions.dropdown_populate(dropdown, item_type)

    def set_data(self, filepath: str, suggested: list):
        self.filepath = filepath
        self.extension = filepath[filepath.rfind('.')+1:]
        self.suggested = suggested
        self.doc = os.path.basename(filepath)

        if len(self.suggested[0]) > 0:
            self.entry_date.set_text(self.suggested[0])
        self._set_suggestion(self.dpdCountry, self.suggested[1])
        self._set_suggestion(self.dpdGroup, self.suggested[2])
        self._set_suggestion(self.dpdSubgroup, self.suggested[3])
        self._set_suggestion(self.dpdSentBy, self.suggested[4])
        self._set_suggestion(self.dpdPurpose, self.suggested[5])
        if len(self.suggested[6]) > 0:
            self.entry_concept.set_text(self.suggested[6])
        self._set_suggestion(self.dpdSentTo, self.suggested[7])
        self.lblExt.set_text(self.extension)
        self.lblFilenameCur.set_markup(self.doc)
        self.lblFilenameCur.set_selectable(True)
        self.lblFilenameNew.set_markup(self.result)
        self.lblFilenameNew.set_selectable(True)
        self.btnPreview.connect('clicked', self.on_document_display, self.filepath)


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
        dropdown = self.factory.create_dropdown_generic(item_type, ellipsize=False) #, item)
        self.actions.dropdown_populate(dropdown, item_type)
        boxValue.append(dropdown)
        boxValue.append(button)
        return row, button, dropdown

    def _set_suggestion(self, dropdown, suggestion):
        found = False
        if len(suggestion) > 0:
            model = dropdown.get_model()
            # ~ self.log.debug("%s > %s", dropdown, model)
            n = 0
            for item in model:
                # ~ self.log.debug(item)
                # ~ self.log.debug("%s == %s? %s (n=%d)", item.id, suggestion, item.id == suggestion, n)
                if item.id == suggestion:
                    dropdown.set_selected(n)
                    found = True
                n += 1

        # ~ if not found:
            # ~ dropdown.set_selected(0)

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
        self.entry_date.connect('changed', self.on_changed_entry)

    def __create_field_1_country(self):
        self.rowCountry, self.btnCountry, self.dpdCountry = self.__create_actionrow('Country', Country, 'countries')
        self.dropdowns.append((self.dpdCountry, Country))
        self.btnCountry.connect('clicked', self.on_country_manage)
        self.dpdCountry.connect("notify::selected-item", self.on_changed_entry)
        config = self.config['Country'].connect('repo-settings-updated-countries', self.update_countries)

    def __create_field_2_group(self):
        self.rowGroup, self.btnGroup, self.dpdGroup = self.__create_actionrow('Group', Group, 'groups')
        self.dropdowns.append((self.dpdGroup, Group))
        self.btnGroup.connect('clicked', self.on_group_manage)
        self.dpdGroup.connect("notify::selected-item", self.on_changed_entry)

    def __create_field_3_subgroup(self):
        self.rowSubgroup, self.btnSubgroup, self.dpdSubgroup = self.__create_actionrow('Subgroup', Subgroup, 'subgroups')
        self.dropdowns.append((self.dpdSubgroup, Subgroup))
        self.btnSubgroup.connect('clicked', self.on_subgroup_add)
        self.dpdSubgroup.connect("notify::selected-item", self.on_changed_entry)

    def __create_field_4_sentby(self):
        self.rowSentBy, self.btnSentBy, self.dpdSentBy = self.__create_actionrow('Sent by', Person, 'People')
        self.dropdowns.append((self.dpdSentBy, Person))
        self.btnSentBy.connect('clicked', self.on_person_sentby_add)
        self.dpdSentBy.connect("notify::selected-item", self.on_changed_entry)

    def __create_field_5_purpose(self):
        self.rowPurpose, self.btnPurpose, self.dpdPurpose = self.__create_actionrow('Purpose', Purpose, 'purposes')
        self.dropdowns.append((self.dpdPurpose, Purpose))
        self.dpdPurpose.connect("notify::selected-item", self.on_changed_entry)

    def __create_field_6_concept(self):
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
        self.entry_concept.set_width_chars(41)
        self.entry_concept.set_alignment(1.0)
        self.entry_concept.set_placeholder_text('Type anything here...')
        boxValue.append(self.entry_concept)
        boxValue.append(button)
        self.entry_concept.connect('changed', self.on_changed_entry)

    def __create_field_7_sentto(self):
        self.rowSentTo, self.btnSentTo, self.dpdSentTo = self.__create_actionrow('Sent to', Person, 'People')
        self.dropdowns.append((self.dpdSentTo, Person))
        self.btnSentTo.connect('clicked', self.on_person_sentto_add)
        self.dpdSentTo.connect("notify::selected-item", self.on_changed_entry)

    def __create_field_8_extension(self):
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

    def __create_field_9_result(self, *args):
        """Field 7. extension"""
        # Current filename
        self.row_cur_filename = Adw.ActionRow.new()
        self.row_cur_filename.set_title("Current filename")
        boxValueCur = self.__create_box_value()
        self.lblFilenameCur = Gtk.Label()
        self.row_cur_filename.add_suffix(self.lblFilenameCur)
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
        self.row_new_filename.add_suffix(self.lblFilenameNew)
        self.boxMain.append(self.row_new_filename)

    def update_countries(self, *args):
        self.actions.dropdown_populate(self.dpdCountry, Country)
        self.log.debug("Country dropdown updated")

    def _on_response_rename(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            source = self.get_filepath_source()
            target = os.path.join(os.path.dirname(source), self.get_filepath_target())
            shutil.move(source, target)
            self.log.debug("Rename document from '%s' to '%s'", os.path.basename(source), os.path.basename(target))
            self.backend.check_source()
        # ~ self.destroy()
        self.app.show_stack_page_by_name('workspace')


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
            asubgroup = dropdown_get_selected_item(self.dpdSubgroup)
            sentby = dropdown_get_selected_item(self.dpdSentBy)
            apurpose = dropdown_get_selected_item(self.dpdPurpose)
            aconcept = self.entry_concept.get_text().upper().replace(' ', '_')
            sentto = dropdown_get_selected_item(self.dpdSentTo)
            aextension = self.lblExt.get_text()
            fields.append(adate)        # 0. Date
            fields.append(acountry)     # 1. Country
            fields.append(agroup)       # 2. Group
            fields.append(asubgroup)    # 3. Subgroup
            fields.append(sentby)       # 4. SentBy
            fields.append(apurpose)     # 5. Purpose
            fields.append(aconcept)     # 6. Concept
            fields.append(sentto)       # 7. SentTo
            self.result = "%s.%s" % ('-'.join(fields), aextension)
            self.lblFilenameNew.set_markup(self.result)

            person = self.app.get_config('Person')
            countries = self.app.get_config('Country')
            groups = self.app.get_config('Group')
            subgroups = self.app.get_config('Subgroup')
            purposes = self.app.get_config('Purpose')
            v_date = self.validate_date(adate)
            v_group = len(agroup) > 0
            v_subgroup = len(asubgroup) > 0
            v_cty = countries.exists(acountry)
            v_sentby = person.exists(sentby)
            v_purp = len(apurpose) > 0
            v_cnpt = len(aconcept) > 0
            v_sentto = person.exists(sentto)

            if v_group:
                success_or_warning(self.rowGroup, groups.exists(agroup))
            else:
                success_or_error(self.rowGroup, v_group)

            if v_subgroup:
                success_or_warning(self.rowSubgroup, subgroups.exists(asubgroup))
            else:
                success_or_error(self.rowSubgroup, v_subgroup)

            if v_purp:
                success_or_warning(self.rowPurpose, purposes.exists(apurpose))
            else:
                success_or_error(self.rowPurpose, v_purp)

            success_or_error(self.rowDate, v_date)
            success_or_error(self.rowCountry, v_cty)
            success_or_error(self.rowSentBy, v_sentby)
            success_or_error(self.rowConcept, v_cnpt)
            success_or_error(self.rowSentTo, v_sentto)

            if v_date and v_sentby and v_sentto and v_cty and v_group and v_subgroup and v_purp and v_cnpt:
                self.btnAccept.set_sensitive(True)
            else:
                self.btnAccept.set_sensitive(False)
                pass
        except Exception as error:
            self.log.error(error)
            self.result = ''
            raise

    def validate_date(self, adate: str) -> bool:
        try:
            datetime.strptime(adate, '%Y%m%d')
            return True
        except:
            return False

    def validate(self, fields: list) -> None:
        valid_filename = False

        # Validate Group:
        cnfGroups = self.app.get_config('Group')
        groups = cnfGroups.load()
        if not cnfGroups.exists(fields[2]):
            groups.append(fields[2])
            cnfGroups.save(groups)
            self.new_values.append(('groups', '', fields[2]))

        # Validate Subgroup:
        cnfSubgroups = self.app.get_config('Subgroup')
        subgroups = cnfSubgroups.load()
        if not cnfSubgroups.exists(fields[3]):
            subgroups.append(fields[3])
            cnfSubgroups.save(subgroups)
            self.new_values.append(('subgroups', '', fields[3]))

        # Validate SentBy:
        cnfOrgs = self.app.get_config('Person')
        orgs = cnfOrgs.load()
        if not cnfOrgs.exists(fields[4]):
            cnfOrgs.set(fields[4], '')
            cnfOrgs.save(cnfOrgs)
            self.new_values.append(('Sent by', '', fields[4]))

        # Validate SentTo:
        cnfOrgs = self.app.get_config('Person')
        orgs = cnfOrgs.load()
        if not cnfOrgs.exists(fields[7]):
            cnfOrgs.set(fields[7], '')
            cnfOrgs.save(cnfOrgs)
            self.new_values.append(('To', '', fields[7]))


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
        question = self.factory.create_dialog_question(self.app.win, "Are you sure?", widget)
        question.connect('response', self.on_answer_question_rename)
        question.show()

    def on_answer_question_rename(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            source = self.get_filepath_source()
            target = os.path.join(os.path.dirname(source), self.get_filepath_target())
            self.log.debug("%s => %s", source, target)
            if source != target:
                if not os.path.exists(target):
                    shutil.move(source, target)
                    self.log.info("%s renamed to %s", source, target)
                else:
                    self.log.error("Target already exist. Skip rename")
            else:
                self.log.error("Source and Target are the same. Skip rename")
            dialog.destroy()
        else:
            dialog.destroy()
        self.app.show_stack_page_by_name('workspace')

    def on_rename_cancel(self, *args):
        self.app.show_stack_page_by_name('workspace')
        # ~ self.response(Gtk.ResponseType.CANCEL)
        # ~ self.destroy()

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

    def on_people_refresh(self, *args):
        config = self.app.get_config('Person')
        people = config.load(config.config_local)
        model = self.combobox_from.get_model()
        model.clear()
        for alias in people:
            model.append([alias, "<i>%s</i>" % people[alias]])

        model = self.combobox_to.get_model()
        model.clear()
        for alias in people:
            model.append([alias, "<i>%s</i>" % people[alias]])


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
            self.app.show_workspace()
            # ~ dialog.destroy()
            # ~ self.response(Gtk.ResponseType.CANCEL)

    def on_person_sentby_add(self, *args):
        dialog = MiAZDialogAdd(self.app, self.get_root(), 'Add new person or entity', 'Initials', 'Full name')
        dialog.connect('response', self.on_response_person_sentby_add)
        dialog.show()

    def on_country_manage(self, *args):
        box = self.factory.create_box_vertical(spacing=12, vexpand=True, hexpand=True)
        selector = MiAZCountries(self.app)
        selector.set_vexpand(True)
        selector.update()
        box.append(selector)
        dialog = self.factory.create_dialog(self.app.win, 'Manage countries', box, 800, 600)
        dialog.show()

    def on_group_manage(self, *args):
        box = self.factory.create_box_vertical(spacing=12, vexpand=True, hexpand=True)
        selector = MiAZGroups(self.app)
        selector.set_vexpand(True)
        selector.update()
        box.append(selector)
        dialog = self.factory.create_dialog(self.app.win, 'Manage groups', box, 800, 600)
        dialog.show()

    def on_country_close(self, *args):
        self.actions.dropdown_populate(self.dpdCountry, Country)
        self.dpdCountry.set_selected(0)

    def on_group_add(self, *args):
        dialog = MiAZDialogAdd(self.app, self.get_root(), 'Add new group', 'Group', '')
        boxKey2 = dialog.get_boxKey2()
        boxKey2.set_visible(False)
        dialog.connect('response', self.on_response_group_add)
        dialog.show()

    def on_subgroup_add(self, *args):
        dialog = MiAZDialogAdd(self.app, self.get_root(), 'Add new subgroup', 'Subgroup', '')
        boxKey2 = dialog.get_boxKey2()
        boxKey2.set_visible(False)
        dialog.connect('response', self.on_response_subgroup_add)
        dialog.show()

    def on_person_sentto_add(self, *args):
        dialog = MiAZDialogAdd(self.app, self.get_root(), 'Add new person or entity', 'Initials', 'Full name')
        dialog.connect('response', self.on_response_person_sentto_add)
        dialog.show()

    def on_response_person_sentby_add(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            key = dialog.get_value1()
            value = dialog.get_value2()
            if len(key) > 0 and len(value) > 0:
                config = self.app.get_config('Person')
                config.add(key=key.upper(), value=value)
                # ~ items = config.load(config.config_local)
                # ~ items[key.upper()] = value
                # ~ config.save(items)

                # Update dropdown
                self.actions.dropdown_populate(self.dpdSentBy, Person)
                self.select_dropdown_item(self.dpdSentBy, key)
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

    def on_response_group_add(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            key = dialog.get_value1()
            if len(key) > 0:
                config = self.app.get_config('Group')
                config.add(key)
                self.actions.dropdown_populate(self.dpdGroup, Group)
                self.select_dropdown_item(self.dpdGroup, key)
        dialog.destroy()

    def on_response_subgroup_add(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            key = dialog.get_value1()
            if len(key) > 0:
                config = self.app.get_config('Subgroup')
                config.add(key)
                self.actions.dropdown_populate(self.dpdSubgroup, Subgroup)
                self.select_dropdown_item(self.dpdSubgroup, key)
        dialog.destroy()

    def on_response_person_sentto_add(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            key = dialog.get_value1()
            value = dialog.get_value2()
            if len(key) > 0 and len(value) > 0:
                config = self.app.get_config('Person')
                config.add(key=key.upper(), value=value)
                # ~ items = config.load(config.config_local)
                # ~ items[key.upper()] = value
                # ~ config.save(items)

                # Update combobox from
                model = self.combobox_to.get_model()
                treeiter = model.append([key.upper(), "<i>%s</i>" % value])
                self.combobox_to.set_active_iter(treeiter)
        dialog.destroy()
