#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gi.repository import GObject
from gi.repository import Gtk

def _get_search_entry_widget(self, dropdown):
    popover = dropdown.get_last_child()
    box = popover.get_child()
    box2 = box.get_first_child()
    search_entry = box2.get_first_child() # Gtk.SearchEntry
    return search_entry
