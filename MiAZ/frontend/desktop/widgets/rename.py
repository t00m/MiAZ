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
    def __init__(self, app, filepath, suggested) -> Gtk.Widget:
        super(MiAZRenameDialog, self).__init__()
        self.log = get_logger('MiazRenameDialog')
        self.app = app
        self.filepath = filepath
        self.suggested = suggested
        doc = os.path.basename(filepath)
        self.set_transient_for(self.app.win)
        self.set_modal(True)
        self.dlgHeader = Gtk.HeaderBar()
        self.set_titlebar(self.dlgHeader)
        self.contents = self.get_content_area()

        # Box to be inserted as contents
        self.boxMain = Gtk.Box.new(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.boxMain.set_vexpand(False)
        self.boxMain.set_hexpand(False)
        self.boxMain.set_margin_top(margin=12)
        self.boxMain.set_margin_end(margin=12)
        self.boxMain.set_margin_bottom(margin=12)
        self.boxMain.set_margin_start(margin=12)

        # Fields
        self.boxFields = Gtk.Box.new(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        self.boxFields.set_vexpand(False)
        self.boxFields.set_hexpand(False)
        self.boxFields.set_margin_top(margin=12)
        self.boxFields.set_margin_end(margin=12)
        self.boxFields.set_margin_bottom(margin=12)
        self.boxFields.set_margin_start(margin=12)

        # Filename format: {timestamp}-{country}-{collection}-{from}-{purpose}-{concept}-{to}.{extension}
        self.__create_field_0_date() # Field 1. Country
        self.__create_field_1_country() # Field 3. From
        self.__create_field_2_collection() # Field 2. Collection
        self.__create_field_3_from() # Field 3. From
        self.__create_field_4_purpose() # Field 3. Purpose
        self.__create_field_5_concept() # Field 3. Concept
        self.__create_field_6_to() # Field 6. To
        self.__create_field_7_extension() # Field 7. Extension

        # Box Suggested Filename
        # ~ boxSuggested = Gtk.CenterBox()
        # ~ self.lblSuggestedTitle = Gtk.Label()
        # ~ self.lblSuggestedTitle.set_markup('<big>Suggested Filename: </big>')
        # ~ boxSuggested.append(self.lblSuggestedTitle)

        # ~ self.lblSuggestedFilename = Gtk.Label()
        # ~ self.lblSuggestedFilename.set_markup("<big><b>%s.%s</b></big>" % ('-'.join(suggested), ext))
        # ~ self.lblSuggestedFilename.set_selectable(True)
        # ~ boxSuggested.set_center_widget(self.lblSuggestedFilename)
        # ~ boxSuggested.set_visible(False)
        # ~ self.boxFields.append(boxSuggested)

        self.boxMain.append(self.boxFields)


        self.contents.append(self.boxMain)
        self.add_buttons('Cancel', Gtk.ResponseType.CANCEL, 'Accept', Gtk.ResponseType.ACCEPT)
        btnAccept = self.get_widget_for_response(Gtk.ResponseType.ACCEPT)
        btnAccept.get_style_context().add_class(class_name='success')
        btnCancel = self.get_widget_for_response(Gtk.ResponseType.CANCEL)
        btnCancel.get_style_context().add_class(class_name='error')

        self.on_changed_entry()

    def __create_box_field(self) -> Gtk.Box:
        box = Gtk.Box.new(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        box.set_hexpand(True)
        box.set_homogeneous(False)
        return box

    def __create_box_key(self, title: str) -> Gtk.Box:
        box = Gtk.Box.new(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        box.set_hexpand(True)
        label = Gtk.Label()
        label.set_markup('<b>%30s</b>' % title)
        label.set_xalign(1.0)
        box.append(label)
        return box

    def __create_box_value(self) -> Gtk.Box:
        box = Gtk.Box.new(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        box.set_hexpand(True)
        return box

    def __create_field_0_date(self):
        """Field 0. Date"""
        boxField = self.__create_box_field()
        boxKey = self.__create_box_key('Date')
        boxValue = self.__create_box_value()
        boxField.append(boxKey)
        boxField.append(boxValue)
        self.boxFields.append(boxField)

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

        return boxField

    def __create_field_1_country(self):
        boxField = self.__create_box_field()
        boxKey = self.__create_box_key('Country')
        boxValue = self.__create_box_value()
        boxField.append(boxKey)
        boxField.append(boxValue)
        self.boxFields.append(boxField)

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

        return boxField


    def __create_field_2_collection(self):
        """Field 2. Collections"""
        boxField = self.__create_box_field()
        boxKey = self.__create_box_key('Collection')
        boxValue = self.__create_box_value()
        boxField.append(boxKey)
        boxField.append(boxValue)
        self.boxFields.append(boxField)

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

        return boxField

    def __create_field_4_purpose(self):
        """Field 2. purposes"""
        boxField = self.__create_box_field()
        boxKey = self.__create_box_key('Purpose')
        boxValue = self.__create_box_value()
        boxField.append(boxKey)
        boxField.append(boxValue)
        self.boxFields.append(boxField)

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

        return boxField

    def __create_field_5_concept(self):
        """Field 2. concepts"""
        boxField = self.__create_box_field()
        boxKey = self.__create_box_key('Concept')
        boxValue = self.__create_box_value()
        boxField.append(boxKey)
        boxField.append(boxValue)
        self.boxFields.append(boxField)

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

        return boxField

    def __create_field_3_from(self):
        """Field 3. From"""
        boxField = self.__create_box_field()
        boxKey = self.__create_box_key('Purpose')
        boxValue = self.__create_box_value()
        boxField.append(boxKey)
        boxField.append(boxValue)
        self.boxFields.append(boxField)

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

        return boxField

    def __create_field_6_to(self):
        """Field 6. To"""
        boxField = self.__create_box_field()
        boxKey = self.__create_box_key('Purpose')
        boxValue = self.__create_box_value()
        boxField.append(boxKey)
        boxField.append(boxValue)
        self.boxFields.append(boxField)

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

        return boxField

    def __create_field_7_extension(self):
        """Field 7. extension"""
        boxField = self.__create_box_field()
        boxKey = self.__create_box_key('Extension')
        boxValue = self.__create_box_value()
        boxField.append(boxKey)
        boxField.append(boxValue)
        self.boxFields.append(boxField)

        model = Gtk.ListStore(str)
        for extension in {}:
            model.append([extension])
        # ~ treeiter = model.append([self.suggested[7]])
        combobox = Gtk.ComboBox.new_with_model_and_entry(model)
        combobox.set_entry_text_column(0)
        # ~ combobox.set_active_iter(treeiter)
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

        return boxField

    def on_changed_entry(self, *args):
        self.lblExt = Gtk.Label() # FIXME!
        suggested = "%s-%s-%s-%s-%s-%s-%s.%s" % (
                                      self.entry_date.get_text(),
                                      self.entry_country.get_text(),
                                      self.entry_collection.get_text(),
                                      self.entry_from.get_text(),
                                      self.entry_purpose.get_text(),
                                      self.entry_concept.get_text(),
                                      self.entry_to.get_text(),
                                      self.lblExt.get_text()
                                    )
        self.log.debug(suggested)
        # ~ self.lblSuggestedFilename.set_markup("<big><b>%s</b></big>" % suggested)