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

class RenameDialog(Gtk.Dialog):
    def __init__(self, app, filepath, suggested) -> Gtk.Widget:
        super(RenameDialog, self).__init__()
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
        # ~ fields = ['date', 'country', 'collection', 'from', 'purpose', 'concept', 'to']

        # Field 0. Date
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

        # Field 1. Country
        box = Gtk.Box.new(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        box.set_hexpand(False)
        label = Gtk.Label()
        label.set_markup('<b>Country</b>')
        label.set_xalign(0.0)
        box.append(label)
        entry = Gtk.Entry()
        entry.set_has_frame(True)
        entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, 'miaz-res-country')
        entry.set_text(self.suggested[1])
        box.append(entry)
        self.boxFields.append(box)



        self.__create_field_collection() # Field 2. Collection
        # ~ self.boxFields.append(box)

        # ~ n = 0
        # ~ for item in fields:
            # ~ box = Gtk.Box.new(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            # ~ box.set_hexpand(False)
            # ~ label = Gtk.Label()
            # ~ label.set_markup('<b>%s</b>' % item.title())
            # ~ label.set_xalign(0.0)
            # ~ box.append(label)
            # ~ entry = Gtk.Entry()
            # ~ entry.set_has_frame(True)
            # ~ entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, 'miaz-res-%s' % item)
            # ~ entry.set_text(suggested[n])
            # ~ box.append(entry)
            # ~ self.boxFields.append(box)
            # ~ n += 1

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