#!/usr/bin/python3
# File: searchbar.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Custom SearchBar widget
# Borrowed from: https://github.com/timlau/gtk4-python

from gi.repository import Gtk

class SearchBar(Gtk.SearchBar):
    """ Wrapper for Gtk.Searchbar Gtk.SearchEntry"""

    def __init__(self, app):
        super().__init__()
        self.app = app
        window = self.app.get_widget('window')
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_spacing(24)

        # Add SearchEntry
        entry = self.app.add_widget('searchbar_entry', Gtk.SearchEntry())
        entry.set_hexpand(True)
        box.append(entry)
        self.set_child(box)

        # connect search entry to seach bar
        self.connect_entry(entry)

        # set key capture from main window, it will show searchbar, when you start typing
        if window:
            self.set_key_capture_widget(window)

        # show close button in search bar
        self.set_show_close_button(True)

        # Set search mode to off by default
        self.set_search_mode(False)

    def set_callback(self, callback):
        """ Connect the search entry activate to an callback handler"""
        entry = self.app.get_widget('searchbar_entry')
        entry.connect('changed', callback)
