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

        # Fields
        self.boxFields = Gtk.Box.new(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        self.boxFields.set_vexpand(False)
        self.boxFields.set_hexpand(False)
        self.boxFields.set_margin_top(margin=6)
        self.boxFields.set_margin_end(margin=6)
        self.boxFields.set_margin_bottom(margin=6)
        self.boxFields.set_margin_start(margin=6)

        # Filename format: {timestamp}-{country}-{collection}-{from}-{purpose}-{concept}-{to}.{extension}
        self.__create_field_date() # Field 1. Country
        self.__create_field_country() # Field 3. From
        self.__create_field_collection() # Field 2. Collection
        self.__create_field_from() # Field 3. From
        self.__create_field_to() # Field 6. To

        box = Gtk.Box.new(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        box.set_hexpand(False)
        label = Gtk.Label()
        label.set_markup('<b>Extension</b>')
        label.set_xalign(0.0)
        box.append(label)
        ext = filepath[filepath.rfind('.')+1:]
        lblExt = Gtk.Label()
        lblExt.set_text('.%s' % ext)
        lblExt.set_xalign(0.0)
        lblExt.set_yalign(0.5)
        lblExt.set_vexpand(True)
        box.append(lblExt)
        self.boxFields.append(box)

        self.lblSuggestedFilename = Gtk.Label()
        self.lblSuggestedFilename.set_markup("<i>Suggested filename: </i>%s.%s" % ('-'.join(suggested), ext))
        self.lblSuggestedFilename.set_selectable(True)

        self.boxMain.append(self.boxFields)
        self.boxMain.append(self.lblSuggestedFilename)

        self.contents.append(self.boxMain)
        self.add_buttons('Cancel', Gtk.ResponseType.CANCEL, 'Accept', Gtk.ResponseType.ACCEPT)
        btnAccept = self.get_widget_for_response(Gtk.ResponseType.ACCEPT)
        btnAccept.get_style_context().add_class(class_name='success')
        btnCancel = self.get_widget_for_response(Gtk.ResponseType.CANCEL)
        btnCancel.get_style_context().add_class(class_name='error')

    def __create_field_date(self):
        box = Gtk.Box.new(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        box.set_hexpand(False)
        label = Gtk.Label()
        label.set_markup('<b>Date</b>')
        label.set_xalign(0.0)
        box.append(label)
        entry = Gtk.Entry()
        entry.set_has_frame(True)
        entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, 'miaz-res-date')
        entry.set_text(self.suggested[0])
        box.append(entry)
        self.boxFields.append(box)
        return box

    def __create_field_country(self):
        countries = self.app.get_config('countries')
        box = Gtk.Box.new(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        box.set_hexpand(False)
        label = Gtk.Label()
        label.set_markup('<b>Country</b>')
        label.set_xalign(0.0)
        box.append(label)

        model = Gtk.ListStore(str, str)
        countries = countries.load_global()
        for code in countries:
            model.append([code, "<i>%s</i>" % countries[code]['Country Name']])
        treeiter = model.append([self.suggested[1], "<i>%s</i>" % self.suggested[1]])
        combobox = Gtk.ComboBox.new_with_model_and_entry(model)
        combobox.set_entry_text_column(0)

        renderer = Gtk.CellRendererText()
        combobox.pack_start(renderer, True)
        combobox.add_attribute(renderer, "markup", 1)

        combobox.set_entry_text_column(0)
        combobox.set_active_iter(treeiter)
        entry = combobox.get_child()
        entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, 'miaz-res-country')
        box.append(combobox)
        self.boxFields.append(box)

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
        completion.set_text_column(1)
        entry.set_completion(completion)

        return box


    def __create_field_collection(self):
        """Field 2. Collections"""
        collections = self.app.get_config('collections')
        box = Gtk.Box.new(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        box.set_hexpand(False)
        label = Gtk.Label()
        label.set_markup('<b>Collection</b>')
        label.set_xalign(0.0)
        box.append(label)

        model = Gtk.ListStore(str)
        for collection in collections.load():
            model.append([collection])
        treeiter = model.append([self.suggested[2]])
        combobox = Gtk.ComboBox.new_with_model_and_entry(model)
        combobox.set_entry_text_column(0)
        combobox.set_active_iter(treeiter)
        entry = combobox.get_child()
        entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, 'miaz-res-collection')
        box.append(combobox)
        self.boxFields.append(box)

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
        entry.set_completion(completion)

        return box

    def __create_field_from(self):
        """Field 3. From"""
        organizations = self.app.get_config('organizations')
        box = Gtk.Box.new(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        box.set_hexpand(False)
        label = Gtk.Label()
        label.set_markup('<b>From</b>')
        label.set_xalign(0.0)
        box.append(label)

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
        entry = combobox.get_child()
        entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, 'miaz-res-organization')
        box.append(combobox)
        self.boxFields.append(box)

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
        entry.set_completion(completion)

        return box

    def __create_field_to(self):
        """Field 6. To"""
        organizations = self.app.get_config('organizations')
        box = Gtk.Box.new(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        box.set_hexpand(False)
        label = Gtk.Label()
        label.set_markup('<b>To</b>')
        label.set_xalign(0.0)
        box.append(label)

        model = Gtk.ListStore(str, str)
        organizations = organizations.load()
        for alias in organizations:
            self.log.debug("%s (%s)", alias, organizations[alias])
            model.append([alias, "<i>%s</i>" % organizations[alias]])
        treeiter = model.append([self.suggested[6], "<i>%s</i>" % self.suggested[6]])
        combobox = Gtk.ComboBox.new_with_model_and_entry(model)

        renderer = Gtk.CellRendererText()
        combobox.pack_start(renderer, True)
        combobox.add_attribute(renderer, "markup", 1)

        combobox.set_entry_text_column(0)
        combobox.set_active_iter(treeiter)
        entry = combobox.get_child()
        entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, 'miaz-res-organization')
        box.append(combobox)
        self.boxFields.append(box)

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
        entry.set_completion(completion)

        return box