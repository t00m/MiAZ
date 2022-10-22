#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from abc import abstractmethod

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw
from gi.repository import Gio
from gi.repository import GLib
from gi.repository.GdkPixbuf import Pixbuf

from MiAZ.backend.log import get_logger
from MiAZ.frontend.desktop.widgets.row import MiAZFlowBoxRow

class MiAZRenameDialog(Gtk.Dialog):
    result = ''
    new_values = []

    def __init__(self, app, row: MiAZFlowBoxRow, filepath: str, suggested: list) -> Gtk.Widget:
        super(MiAZRenameDialog, self).__init__()
        self.app = app
        self.factory = self.app.get_factory()
        self.log = get_logger('MiazRenameDialog')
        self.set_size_request(800, 600)
        self.set_transient_for(self.app.win)
        self.set_modal(True)

        # Basic data
        self.row = row
        self.filepath = filepath
        self.extension = filepath[filepath.rfind('.')+1:]
        self.suggested = suggested
        self.doc = os.path.basename(filepath)

        # Header & Butons
        self.btnAccept = self.factory.create_button('', 'rename', self.on_rename_accept)
        self.btnAccept.get_style_context ().add_class ('suggested-action')
        self.btnAccept.set_can_focus(True)
        self.btnAccept.set_receives_default(True)
        btnCancel = self.factory.create_button('', 'cancel', self.on_rename_cancel)
        btnCancel.get_style_context ().add_class ('destructive-action')
        btnDelete = self.factory.create_button('miaz-document-delete', '', self.on_document_delete, data=self.filepath)
        self.set_default_response(Gtk.ResponseType.ACCEPT)
        lblHeaderTitle = Gtk.Label()
        lblHeaderTitle.set_markup('<b>Rename file</b>')
        self.dlgHeader = Adw.HeaderBar()
        self.dlgHeader.set_show_end_title_buttons(False)
        self.dlgHeader.pack_start(btnDelete)
        self.dlgHeader.pack_end(btnCancel)
        self.dlgHeader.pack_end(self.btnAccept)
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
        self.entry_date.connect('changed', self.on_changed_entry)
        self.entry_country.connect('changed', self.on_changed_entry)
        self.entry_collection.connect('changed', self.on_changed_entry)
        self.entry_from.connect('changed', self.on_changed_entry)
        self.entry_purpose.connect('changed', self.on_changed_entry)
        self.entry_concept.connect('changed', self.on_changed_entry)
        self.entry_to.connect('changed', self.on_changed_entry)
        self.on_changed_entry()

    def __create_box_value(self) -> Gtk.Box:
        box = Gtk.Box.new(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.set_hexpand(False)
        box.set_valign(Gtk.Align.CENTER)
        return box

    def __create_completion(self, model: Gtk.ListStore) -> Gtk.EntryCompletion:
        def completion_match_func(completion, key, iter):
            model = completion.get_model()
            text = model.get_value(iter, 0)
            if key.upper() in text.upper():
                return True
            return False

        completion = Gtk.EntryCompletion()
        completion.set_match_func(completion_match_func)
        completion_model = model
        completion.set_model(completion_model)
        completion.set_text_column(0)
        return completion

    def __create_actionrow(self, item: str, model: Gtk.ListStore) -> Adw.ActionRow:
        row = Adw.ActionRow.new()
        row.set_title(item.title())
        row.set_icon_name('miaz-res-%s' % item)
        boxValue = self.__create_box_value()
        row.add_suffix(boxValue)
        self.boxMain.append(row)
        button = self.factory.create_button('miaz-list-add', '')
        combobox = Gtk.ComboBox.new_with_model_and_entry(model)
        combobox.set_entry_text_column(0)
        entry = combobox.get_child()
        entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, 'miaz-res-%s' % item)
        boxValue.append(button)
        boxValue.append(combobox)
        completion = self.__create_completion(model)
        entry.set_completion(completion)
        return row, button, combobox, entry


    def __create_field_0_date(self):
        """Field 0. Date"""
        model = Gtk.ListStore(str)
        row, button, combobox, self.entry_date = self.__create_actionrow('date', model)
        button.set_visible(False)
        for date in {}:
            model.append([date])
        if len(self.suggested[0]) > 0:
            treeiter = model.append([self.suggested[0]])
            combobox.set_active_iter(treeiter)

    # ~ def __create_field_0_date(self):
        # ~ row = Adw.ActionRow.new()
        # ~ row.set_title('Date')
        # ~ row.set_icon_name('miaz-res-date')
        # ~ boxValue = self.__create_box_value()
        # ~ row.add_suffix(boxValue)
        # ~ self.boxMain.append(row)
        # ~ calendar = Gtk.Calendar()
        # ~ self.entry_date = Gtk.Entry()
        # ~ self.entry_date.set_visible(False)
        # ~ boxValue.append(self.entry_date)
        # ~ boxValue.append(calendar)

    def __create_field_1_country(self):
        model = Gtk.ListStore(str, str)
        row, button, combobox, self.entry_country = self.__create_actionrow('country', model)
        button.set_visible(False)
        countries = self.app.get_config('countries')
        my_countries = countries.load()
        all_countries = countries.load_global()
        countries = countries.load_global()
        for code in my_countries:
            model.append([code, "%s" % all_countries[code]['Country Name']])
        if len(self.suggested[1]) > 0:
            treeiter = model.append([self.suggested[1], "%s" % self.suggested[1]])
            combobox.set_active_iter(treeiter)

    def __create_field_2_collection(self):
        """Field 2. Collections"""
        model = Gtk.ListStore(str)
        row, button, combobox, self.entry_collection = self.__create_actionrow('collection', model)
        button.set_visible(False)
        collections = self.app.get_config('collections')
        for collection in collections.load():
            model.append([collection])
        if len(self.suggested[2]) > 0:
            treeiter = model.append([self.suggested[2]])
            combobox.set_active_iter(treeiter)


    def __create_field_3_from(self):
        """Field 3. From"""
        model = Gtk.ListStore(str, str)
        row, button, combobox, self.entry_from = self.__create_actionrow('from', model)
        config = self.app.get_config('organizations')
        organizations = config.load()
        for alias in organizations:
            model.append([alias, "<i>%s</i>" % organizations[alias]])
        if len(self.suggested[3]) > 0:
            treeiter = model.append([self.suggested[3], "%s" % self.suggested[3]])
            combobox.set_active_iter(treeiter)

        renderer = Gtk.CellRendererText()
        combobox.pack_start(renderer, True)
        combobox.add_attribute(renderer, "markup", 1)
        combobox.set_entry_text_column(0)

    def __create_field_4_purpose(self):
        """Field 4. purposes"""
        model = Gtk.ListStore(str)
        row, button, combobox, self.entry_purpose = self.__create_actionrow('purpose', model)
        button.set_visible(False)
        purposes = self.app.get_config('purposes')
        for purpose in purposes.load():
            model.append([purpose])
        if len(self.suggested[4]) > 0:
            treeiter = model.append([self.suggested[4]])
            combobox.set_active_iter(treeiter)

    def __create_field_5_concept(self):
        """Field 5. concepts"""
        model = Gtk.ListStore(str)
        row, button, combobox, self.entry_concept = self.__create_actionrow('concept', model)
        button.set_visible(False)
        concepts = self.app.get_config('concepts')
        for concept in concepts.load():
            model.append([concept])
        if len(self.suggested[5]) > 0:
            treeiter = model.append([self.suggested[5]])
            combobox.set_active_iter(treeiter)

    def __create_field_6_to(self):
        """Field 6. To"""
        model = Gtk.ListStore(str, str)
        row, button, combobox, self.entry_to = self.__create_actionrow('to', model)
        organizations = self.app.get_config('organizations')
        organizations = organizations.load()
        for alias in organizations:
            model.append([alias, "<i>%s</i>" % organizations[alias]])
        if len(self.suggested[6]) > 0:
            treeiter = model.append([self.suggested[6], "%s" % self.suggested[6]])
            combobox.set_active_iter(treeiter)

        renderer = Gtk.CellRendererText()
        combobox.pack_start(renderer, True)
        combobox.add_attribute(renderer, "markup", 1)
        combobox.set_entry_text_column(0)

    def __create_field_7_extension(self):
        """Field 7. extension"""
        model = Gtk.ListStore(str)
        row, button, combobox, self.entry_extension = self.__create_actionrow('extension', model)
        button.set_visible(False)
        extensions = self.app.get_config('extensions')
        for extension in extensions.load_global():
            treeiter = model.append([extension])
            if extension == self.extension:
                active = treeiter
        combobox.set_active_iter(active)
        combobox.set_sensitive(False)

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

        icon = self.app.icman.get_icon_mimetype_from_file(self.filepath, 36, 36)
        icon.set_icon_size(Gtk.IconSize.INHERIT)
        boxFileDisplayButton = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        btnFileDisplay = button = Gtk.Button()
        btnFileDisplay.set_child(icon)
        btnFileDisplay.connect('clicked', self.on_document_display, self.filepath)
        btnFileDisplay.set_valign(Gtk.Align.CENTER)
        btnFileDisplay.set_hexpand(False)
        self.row_cur_filename.add_suffix(btnFileDisplay)

        self.row_new_filename = Adw.ActionRow.new()
        self.row_new_filename.set_title("<b>New filename</b>")
        boxValueNew = self.__create_box_value()
        self.lblFilenameNew = Gtk.Label()
        self.lblFilenameNew.set_markup(self.result)
        self.lblFilenameNew.set_selectable(True)
        self.row_new_filename.add_suffix(self.lblFilenameNew)
        self.boxMain.append(self.row_new_filename)

    def on_changed_entry(self, *args):
        try:
            fields = []
            adate = self.entry_date.get_text().upper()
            acountry = self.entry_country.get_text().upper()
            acollection = self.entry_collection.get_text().upper()
            afrom = self.entry_from.get_text().upper()
            apurpose = self.entry_purpose.get_text().upper()
            aconcept = self.entry_concept.get_text().upper()
            ato = self.entry_to.get_text().upper()
            aextension = self.entry_extension.get_text()
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
            v_from = organizations.get(afrom)
            v_to = organizations.get(ato)
            self.log.debug("%s > %s", v_from, v_to)
            if len(v_from) == 0 and len(v_to) == 0:
                self.btnAccept.set_sensitive(False)
            else:
                self.btnAccept.set_sensitive(True)
        except:
            self.result = ''


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

    def get_row(self):
        return self.row

    def on_rename_accept(self, *args):
        body = "You are about to rename:\n\n<b>%s</b>\n\nto\n\n<b>%s</b>" % (os.path.basename(self.get_filepath_source()), self.get_filepath_target())
        widget = Gtk.Label()
        widget.set_markup(body)
        question = self.factory.create_dialog_question(self, "Are you sure?", widget)
        question.connect('response', self.on_answer_question_rename)
        question.show()

    def on_answer_question_rename(self, dialog, response):
        if response == Gtk.ResponseType.YES:
            self.response(Gtk.ResponseType.ACCEPT)
            dialog.destroy()
            self.destroy()
        else:
            dialog.destroy()
            self.response(Gtk.ResponseType.CANCEL)

    def on_rename_cancel(self, *args):
        self.response(Gtk.ResponseType.CANCEL)
        self.destroy()

    def on_document_display(self, button, filepath):
        self.log.debug("Displaying %s", filepath)
        os.system("xdg-open '%s'" % filepath)

    def on_document_delete(self, button, filepath):
        body = "You are about to <b>delete</b>:\n\n<b>%s</b>" % os.path.basename(filepath)
        widget = Gtk.Label()
        widget.set_markup(body)
        question = self.factory.create_dialog_question(self, "Are you sure?", widget)
        question.connect('response', self.on_answer_question_delete)
        question.show()

    def on_answer_question_delete(self, dialog, response):
        filepath = self.get_filepath_source()
        if response == Gtk.ResponseType.YES:
            try:
                os.unlink(filepath)
                self.response(Gtk.ResponseType.ACCEPT)
                dialog.destroy()
                self.destroy()
            except FileNotFoundError as error:
                self.log.error("Something went wrong: %s", error)
                self.log.error("Doesn't it exist? Really?")
        else:
            dialog.destroy()
            self.response(Gtk.ResponseType.CANCEL)
