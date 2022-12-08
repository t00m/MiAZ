#!/usr/bin/env python3
# https://discourse.gnome.org/t/migrate-from-comboboxtext-to-comborow-dropdown/10565/2

import gi

gi.require_version('Adw', '1')
gi.require_version('Gtk', '4.0')

from gi.repository import Adw, Gio, GObject, Gtk

class Widget(GObject.Object):
    __gtype_name__ = 'Widget'

    def __init__(self, name):
        super().__init__()
        self._name = name

    @GObject.Property
    def name(self):
        return self._name

class ExampleWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="DropDown")

        nodes = []
        for item in dir(Gtk):
            try:
                aclass = type(eval('Gtk.%s' % item))
                if 'gi.types.GObjectMeta' in str(aclass):
                    if item[0].isupper():
                        # ~ print("%s > %s" % (item, aclass))
                        # USE this~ obj = eval('Gtk.%s' % item)
                        nodes.append('Gtk.%s' % item)
            except Exception as error:
                pass

        self.search_text = '' # Initial search text

        # Populate the model
        self.model = Gio.ListStore(item_type=Widget)
        self.sort_model  = Gtk.SortListModel(model=self.model) #, sorter=cv_sorter)
        self.filter_model = Gtk.FilterListModel(model=self.sort_model)
        self.filter = Gtk.CustomFilter.new(self._do_filter_view, self.filter_model)
        self.filter_model.set_filter(self.filter)

        for node in nodes:
            self.model.append(Widget(name=node))

        # Set up the factory
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup)
        factory.connect("bind", self._on_factory_bind)

        self.dd = Gtk.DropDown(model=self.filter_model, factory=factory, hexpand=True)
        self.dd.set_enable_search(True)
        self.dd.connect("notify::selected-item", self._on_selected_item)
        popover = self.dd.get_last_child()
        box = popover.get_child()
        box2 = box.get_first_child()
        search_entry = box2.get_first_child() # Gtk.SearchEntry
        search_entry.connect('search-changed', self._on_search_changed)
        search_entry.connect('activate', self._on_search_activated)

        box = Gtk.Box(spacing=12, hexpand=True, vexpand=True)
        box.props.margin_start = 12
        box.props.margin_end = 12
        box.props.margin_top = 6
        box.props.margin_bottom = 6
        box.append(Gtk.Label(label="Select Widget:"))
        box.append(self.dd)
        self.set_child(box)

    def _on_factory_setup(self, factory, list_item):
        box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        label = Gtk.Label()
        box.append(label)
        list_item.set_child(box)

    def _on_factory_bind(self, factory, list_item):
        box = list_item.get_child()
        label = box.get_first_child()
        widget = list_item.get_item()
        label.set_text(widget.name)

    def _on_selected_item(self, dropdown, _):
        widget = dropdown.get_selected_item()
        try:
            name = widget.name
            obj = eval(name)
            a = set(dir(obj))
            b = set(dir(Gtk.Widget))
            c = a - b
            for item in c:
                print("%s.%s > %s" % (name, item, eval("%s.%s.__doc__" % (name, item))))
                # ~ print("%s > %s" % (item, eval(eval(item.__doc__))))
        except AttributeError as error:
            print("No widget: %s" % error)


    def _on_search_changed(self, search_entry):
        self.search_text = search_entry.get_text()
        self.filter.changed(Gtk.FilterChange.DIFFERENT)

    def _on_search_activated(self, *args):
        print(args)

    def _do_filter_view(self, item, filter_list_model):
        if self.search_text.upper() in item.name.upper():
            display = True
        else:
            display = False
        print("Searching '%s' in '%s'. Display? %s" % (self.search_text,
                                                    item.name,
                                                    display))
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
