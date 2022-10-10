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

from MiAZ.backend.log import get_logger
from gi.repository.GdkPixbuf import Pixbuf

class MiAZRenameDialog(Gtk.Dialog):
    result = ''

    def __init__(self, app, filepath: str, suggested: list) -> Gtk.Widget:
        super(MiAZRenameDialog, self).__init__()
        self.app = app
        self.log = get_logger('MiazRenameDialog')
        self.set_size_request(800, 600)
        self.set_transient_for(self.app.win)
        self.set_modal(True)


        # Basic data
        self.filepath = filepath
        self.extension = filepath[filepath.rfind('.')+1:]
        self.suggested = suggested
        self.doc = os.path.basename(filepath)

        # Header
        btnAccept = self.app.create_button('', 'rename', self.on_rename_accept)
        btnAccept.get_style_context ().add_class ('suggested-action')
        btnCancel = self.app.create_button('', 'cancel', self.on_rename_cancel)
        btnCancel.get_style_context ().add_class ('destructive-action')
        lblHeaderTitle = Gtk.Label()
        lblHeaderTitle.set_markup('<b>Rename file</b>')
        self.dlgHeader = Adw.HeaderBar()
        self.dlgHeader.set_show_end_title_buttons(False)
        self.dlgHeader.pack_start(btnCancel)
        self.dlgHeader.pack_end(btnAccept)
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
        self.on_changed_entry()

    def __create_box_value(self) -> Gtk.Box:
        box = Gtk.Box.new(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        box.set_hexpand(False)
        box.set_valign(Gtk.Align.CENTER)
        return box

    def __create_field_0_date(self):
        """Field 0. Date"""
        row = Adw.ActionRow.new()
        row.set_title("Date")
        row.set_icon_name('miaz-res-date')
        boxValue = self.__create_box_value()
        row.add_suffix(boxValue)
        self.boxMain.append(row)

        model = Gtk.ListStore(str)
        for date in {}:
            model.append([date])
        treeiter = model.append([self.suggested[0]])
        combobox = Gtk.ComboBox.new_with_model_and_entry(model)
        combobox.set_entry_text_column(0)
        combobox.set_active_iter(treeiter)
        self.entry_date = combobox.get_child()
        self.entry_date.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, 'miaz-res-date')
        self.entry_date.connect('changed', self.on_changed_entry)
        boxValue.append(combobox)

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
        self.entry_date.set_completion(completion)

        # ~ return boxField

    def __create_field_1_country(self):
        row = Adw.ActionRow.new()
        row.set_title("Country")
        row.set_icon_name('miaz-res-country')
        boxValue = self.__create_box_value()
        row.add_suffix(boxValue)
        self.boxMain.append(row)

        countries = self.app.get_config('countries')
        my_countries = countries.load()
        all_countries = countries.load_global()
        model = Gtk.ListStore(str, str)
        countries = countries.load_global()
        for code in my_countries:
            model.append([code, "%s" % all_countries[code]['Country Name']])
        treeiter = model.append([self.suggested[1], "%s" % self.suggested[1]])
        combobox = Gtk.ComboBox.new_with_model_and_entry(model)
        combobox.set_entry_text_column(0)

        renderer = Gtk.CellRendererText()
        combobox.pack_start(renderer, True)
        combobox.add_attribute(renderer, "text", 1)

        combobox.set_entry_text_column(0)
        combobox.set_active_iter(treeiter)
        self.entry_country = combobox.get_child()
        self.entry_country.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, 'miaz-res-country')
        self.entry_country.connect('changed', self.on_changed_entry)
        boxValue.append(combobox)


        def completion_match_func(completion, key, iter):
            model = completion.get_model()
            code = model.get_value(iter, 0)
            name = model.get_value(iter, 1)
            country = code+name
            if key.upper() in country.upper():
                return True
            return False

        completion = Gtk.EntryCompletion()
        completion.set_match_func(completion_match_func)
        completion_model = model
        completion.set_model(completion_model)
        completion.set_text_column(0)
        self.entry_country.set_completion(completion)

    def __create_field_2_collection(self):
        """Field 2. Collections"""
        row = Adw.ActionRow.new()
        row.set_title("Collection")
        row.set_icon_name('miaz-res-collection')
        boxValue = self.__create_box_value()
        row.add_suffix(boxValue)
        self.boxMain.append(row)

        collections = self.app.get_config('collections')
        model = Gtk.ListStore(str)
        for collection in collections.load():
            model.append([collection])
        treeiter = model.append([self.suggested[2]])
        combobox = Gtk.ComboBox.new_with_model_and_entry(model)
        combobox.set_entry_text_column(0)
        combobox.set_active_iter(treeiter)
        self.entry_collection = combobox.get_child()
        self.entry_collection.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, 'miaz-res-collection')
        self.entry_collection.connect('changed', self.on_changed_entry)
        boxValue.append(combobox)

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
        self.entry_collection.set_completion(completion)

    def __create_field_4_purpose(self):
        """Field 4. purposes"""
        row = Adw.ActionRow.new()
        row.set_title("Purpose")
        row.set_icon_name('miaz-res-purpose')
        boxValue = self.__create_box_value()
        row.add_suffix(boxValue)
        self.boxMain.append(row)

        purposes = self.app.get_config('purposes')
        model = Gtk.ListStore(str)
        for purpose in purposes.load():
            model.append([purpose])
        treeiter = model.append([self.suggested[4]])
        combobox = Gtk.ComboBox.new_with_model_and_entry(model)
        combobox.set_entry_text_column(0)
        combobox.set_active_iter(treeiter)
        self.entry_purpose = combobox.get_child()
        self.entry_purpose.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, 'miaz-res-purpose')
        self.entry_purpose.connect('changed', self.on_changed_entry)
        boxValue.append(combobox)

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
        self.entry_purpose.set_completion(completion)

    def __create_field_5_concept(self):
        """Field 5. concepts"""
        row = Adw.ActionRow.new()
        row.set_title("Concept")
        row.set_icon_name('miaz-res-concept')
        boxValue = self.__create_box_value()
        row.add_suffix(boxValue)
        self.boxMain.append(row)

        model = Gtk.ListStore(str)
        for concept in {}:
            model.append([concept])
        treeiter = model.append([self.suggested[5]])
        combobox = Gtk.ComboBox.new_with_model_and_entry(model)
        combobox.set_entry_text_column(0)
        combobox.set_active_iter(treeiter)
        self.entry_concept = combobox.get_child()
        self.entry_concept.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, 'miaz-res-concept')
        self.entry_concept.connect('changed', self.on_changed_entry)
        boxValue.append(combobox)

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
        self.entry_concept.set_completion(completion)

    def __create_field_3_from(self):
        """Field 3. From"""
        row = Adw.ActionRow.new()
        row.set_title("From")
        row.set_icon_name('miaz-res-from')
        boxValue = self.__create_box_value()
        row.add_suffix(boxValue)
        self.boxMain.append(row)

        organizations = self.app.get_config('organizations')
        model = Gtk.ListStore(str, str)
        organizations = organizations.load()
        for alias in organizations:
            model.append([alias, "<i>%s</i>" % organizations[alias]])
        treeiter = model.append([self.suggested[3], "<i>%s</i>" % self.suggested[3]])
        combobox = Gtk.ComboBox.new_with_model_and_entry(model)
        renderer = Gtk.CellRendererText()
        combobox.pack_start(renderer, True)
        combobox.add_attribute(renderer, "markup", 1)
        combobox.set_entry_text_column(0)
        combobox.set_active_iter(treeiter)
        self.entry_from = combobox.get_child()
        self.entry_from.connect('changed', self.on_changed_entry)
        self.entry_from.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, 'miaz-res-organization')
        boxValue.append(combobox)

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
        self.entry_from.set_completion(completion)

    def __create_field_6_to(self):
        """Field 6. To"""
        row = Adw.ActionRow.new()
        row.set_title("To")
        row.set_icon_name('miaz-res-to')
        boxValue = self.__create_box_value()
        row.add_suffix(boxValue)
        self.boxMain.append(row)

        organizations = self.app.get_config('organizations')
        model = Gtk.ListStore(str, str)
        organizations = organizations.load()
        for alias in organizations:
            model.append([alias, "<i>%s</i>" % organizations[alias]])
        treeiter = model.append([self.suggested[6], "<i>%s</i>" % self.suggested[6]])
        combobox = Gtk.ComboBox.new_with_model_and_entry(model)

        renderer = Gtk.CellRendererText()
        combobox.pack_start(renderer, True)
        combobox.add_attribute(renderer, "markup", 1)

        combobox.set_entry_text_column(0)
        combobox.set_active_iter(treeiter)
        self.entry_to = combobox.get_child()
        self.entry_to.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, 'miaz-res-organization')
        self.entry_to.connect('changed', self.on_changed_entry)
        boxValue.append(combobox)

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
        self.entry_to.set_completion(completion)

    def __create_field_7_extension(self):
        """Field 7. extension"""
        row = Adw.ActionRow.new()
        row.set_title("Extension")
        row.set_icon_name('miaz-res-extension')
        boxValue = self.__create_box_value()
        row.add_suffix(boxValue)
        self.boxMain.append(row)

        extensions = self.app.get_config('extensions')
        model = Gtk.ListStore(str)
        for extension in extensions.load_global():
            treeiter = model.append([extension])
            if extension == self.extension:
                active = treeiter
        combobox = Gtk.ComboBox.new_with_model_and_entry(model)
        combobox.set_entry_text_column(0)
        combobox.set_active_iter(active)
        self.entry_extension = combobox.get_child()
        self.entry_extension.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, 'miaz-res-extension')
        self.entry_extension.connect('changed', self.on_changed_entry)
        boxValue.append(combobox)

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
        self.entry_extension.set_completion(completion)

    def __create_field_8_result(self, *args):
        """Field 7. extension"""
        # Current filename
        self.row_cur_filename = Adw.ActionRow.new()
        self.row_cur_filename.set_title("Current filename")
        boxValueCur = self.__create_box_value()
        lblFilenameCur = Gtk.Label()
        lblFilenameCur.set_markup(self.doc)
        self.row_cur_filename.add_suffix(lblFilenameCur)
        self.boxMain.append(self.row_cur_filename)

        icon = self.app.icman.get_icon_mimetype_from_file(self.filepath, 36, 36)
        icon.set_icon_size(Gtk.IconSize.INHERIT)
        boxFileDisplayButton = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        btnFileDisplay = button = Gtk.Button()
        btnFileDisplay.set_child(icon)
        btnFileDisplay.connect('clicked', self.on_display_document, self.filepath)
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
        self.result = "%s-%s-%s-%s-%s-%s-%s.%s" % (
                                      self.entry_date.get_text(),
                                      self.entry_country.get_text(),
                                      self.entry_collection.get_text(),
                                      self.entry_from.get_text(),
                                      self.entry_purpose.get_text(),
                                      self.entry_concept.get_text(),
                                      self.entry_to.get_text(),
                                      self.entry_extension.get_text()
                                    )
        self.lblFilenameNew.set_markup(self.result)

    def get_original(self) -> str:
        return self.filepath

    def get_suggested(self) -> str:
        return self.result

    def on_rename_accept(self, *args):
        body = "You are about to rename '%s' to '%s'" % (self.get_original(), self.get_suggested())
        # ~ question = self.app.message_dialog_question(self, "Are you sure?", body)
        question = Gtk.MessageDialog.new_with_markup(self, Gtk.DialogFlags.MODAL, Gtk.MessageType.QUESTION, Gtk.ButtonsType.YES_NO, "Are you sure")
        question.connect('response', self.on_answer_question)

    def on_rename_cancel(self, *args):
        self.response(Gtk.ResponseType.CANCEL)
        self.destroy()

    def on_answer_question(self, dialog, response):
        if response == Gtk.ResponseType.YES:
            self.destroy()

    def on_display_document(self, button, filepath):
        os.system("xdg-open '%s'" % filepath)