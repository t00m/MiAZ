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

        # Populate the model
        # ~ self.model = Gtk.SingleSelection(Gio.ListStore.new(item_type=Country))
        self.model = Gio.ListStore(item_type=Country)
        for n in nodes.keys():
            self.model.append(Country(country_id=n, country_name=nodes[n]))

        # Set up the factory
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup)
        factory.connect("bind", self._on_factory_bind)

        self.dd = Gtk.ListView(model=Gtk.SingleSelection.new(self.model), factory=factory, hexpand=True)
        self.dd.connect("notify::selected-item", self._on_selected_item_notify)

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
        print(country)


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
