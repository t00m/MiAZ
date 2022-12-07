#!/usr/bin/env python3
# https://discourse.gnome.org/t/migrate-from-comboboxtext-to-comborow-dropdown/10565/2

import os
import gi

gi.require_version('Adw', '1')
gi.require_version('Gtk', '4.0')

from gi.repository import Adw, Gio, GObject, Gtk


class Country(GObject.Object):
    __gtype_name__ = 'Country'

    def __init__(self, country_id, country_name):
        super().__init__()

        self._country_id = country_id
        self._country_name = country_name

    @GObject.Property
    def country_id(self):
        return self._country_id

    @GObject.Property
    def country_name(self):
        return self._country_name

    # ~ @GObject.Property
    # ~ def country_flag(self):
        # ~ return self._country_flag


class ExampleWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="DropDown")

        nodes = {
            "au": "Austria",
            "uk": "United Kingdom",
            "us": "United States",
        }

        self.search_text = '' # Initial search text

        # Populate the model
        self.model = Gio.ListStore(item_type=Country)
        self.sort_model  = Gtk.SortListModel(model=self.model) #, sorter=cv_sorter)
        self.filter_model = Gtk.FilterListModel(model=self.sort_model)
        self.filter = Gtk.CustomFilter.new(self._do_filter_view, self.filter_model)
        self.filter_model.set_filter(self.filter)

        for n in nodes.keys():
            self.model.append(Country(country_id=n, country_name=nodes[n]))

        # Set up the factory
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup)
        factory.connect("bind", self._on_factory_bind)


        self.dd = Gtk.DropDown(model=self.filter_model, factory=factory, hexpand=True)
        self.dd.set_enable_search(True)
        # ~ self.dd.connect("notify", self._on_selected_item_notify)
        # ~ expression = self.dd.get_expression()
        # ~ print(type(expression))
        # ~ print(expression)
        self.dd.connect("notify::selected-item", self._on_selected_item_notify)
        popover = self.dd.get_last_child()
        box = popover.get_child()
        box2 = box.get_first_child()
        search_entry = box2.get_first_child() # Gtk.SearchEntry
        search_entry.connect('search-changed', self._on_search_changed)
        search_entry.connect('activate', self._on_search_activated)

        # ~ cv_sorter = self.dd.get_sorter()


        # ~ self.dd.set_filter(self._do_filter_view)

        box = Gtk.Box(spacing=12, hexpand=True, vexpand=True)
        box.props.margin_start = 12
        box.props.margin_end = 12
        box.props.margin_top = 6
        box.props.margin_bottom = 6
        box.append(Gtk.Label(label="Select Country:"))
        box.append(self.dd)
        self.set_child(box)

    # Set up the child of the list item; this can be an arbitrarily
    # complex widget but we use a simple label now
    def _on_factory_setup(self, factory, list_item):
        box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        label = Gtk.Label()
        image = Gtk.Image()
        box.append(label)
        box.append(image)
        list_item.set_child(box)

    # Bind the item in the model to the row widget; again, since
    # the object in the model can contain multiple properties, and
    # the list item can contain any arbitrarily complex widget, we
    # can have very complex rows instead of the simple cell renderer
    # layouts in GtkComboBox
    def _on_factory_bind(self, factory, list_item):
        # ~ label = list_item.get_child()
        # ~ country = list_item.get_item()
        # ~ label.set_text(country.country_name)
        box = list_item.get_child()
        label = box.get_first_child()
        image = box.get_last_child()
        country = list_item.get_item()
        label.set_text(country.country_name)
        country_flag = os.path.join('flags', '%s.svg' % country.country_id.upper())
        image.set_from_file(country_flag)


    # The notify signal is fired when the selection changes
    def _on_selected_item_notify(self, dropdown, _):
        country = dropdown.get_selected_item()
        try:
            print(country.country_name)
        except AttributeError:
            print("No country")


    def _on_search_changed(self, search_entry):
        self.search_text = search_entry.get_text()
        self.filter.changed(Gtk.FilterChange.DIFFERENT)

    def _on_search_activated(self, *args):
        print(args)

    def _do_filter_view(self, item, filter_list_model):
        if self.search_text.upper() in item.country_name.upper():
            display = True
        else:
            display = False
        print("Searching '%s' in '%s'. Display? %s" % (self.search_text,
                                                    item.country_name,
                                                    display))
        # ~ print("Display %s? %s" % (item.country_name, display))
        return display

class ExampleApp(Adw.Application):
    def __init__(self):
        super().__init__()
        self.window = None

    def do_activate(self):
        if self.window is None:
            self.window = ExampleWindow(self)
        self.window.present()


app = ExampleApp()
app.run([])
