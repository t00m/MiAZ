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

class Method(GObject.Object):
    __gtype_name__ = 'Method'

    def __init__(self, name):
        super().__init__()
        self._name = name

    @GObject.Property
    def name(self):
        return self._name

class ExampleWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="GTK4 Widgets and methods")
        self.search_text_widget = '' # Initial search text for widgets
        self.search_text_method = '' # Initial search text for methods

        # Setup widget dropdown
        ## Widget model
        self.model_widget = Gio.ListStore(item_type=Widget)
        self.sort_model_widget  = Gtk.SortListModel(model=self.model_widget)
        self.filter_model_widget = Gtk.FilterListModel(model=self.sort_model_widget)
        self.filter_widget = Gtk.CustomFilter.new(self._do_filter_widget_view, self.filter_model_widget)
        self.filter_model_widget.set_filter(self.filter_widget)

        for item in dir(Gtk):
            aclass = type(eval('Gtk.%s' % item))
            if 'gi.types.GObjectMeta' in str(aclass):
                if item[0].isupper() and item != 'Widget':
                    self.model_widget.append(Widget(name='Gtk.%s' % item))

        ## Setup DropDown widget factory
        factory_widget = Gtk.SignalListItemFactory()
        factory_widget.connect("setup", self._on_factory_widget_setup)
        factory_widget.connect("bind", self._on_factory_widget_bind)

        self.ddwdg = Gtk.DropDown(model=self.filter_model_widget, factory=factory_widget)
        self.ddwdg.set_enable_search(True)
        self.ddwdg.connect("notify::selected-item", self._on_selected_widget)
        search_entry_widget = self._get_search_entry_widget(self.ddwdg)
        search_entry_widget.connect('search-changed', self._on_search_widget_changed)

        # Setup Method dropdown
        ## Method model
        self.model_method = Gio.ListStore(item_type=Method)
        self.sort_model_method  = Gtk.SortListModel(model=self.model_method)
        self.filter_model_method = Gtk.FilterListModel(model=self.sort_model_method)
        self.filter_method = Gtk.CustomFilter.new(self._do_filter_method_view, self.filter_model_method)
        self.filter_model_method.set_filter(self.filter_method)

        ## Setup DropDown Method factory
        factory_method = Gtk.SignalListItemFactory()
        factory_method.connect("setup", self._on_factory_method_setup)
        factory_method.connect("bind", self._on_factory_method_bind)

        self.ddmth = Gtk.DropDown(model=self.filter_model_method, factory=factory_method)
        self.ddmth.set_enable_search(True)
        self.ddmth.connect("notify::selected-item", self._on_selected_method)
        search_entry_method = self._get_search_entry_widget(self.ddmth)
        search_entry_method.connect('search-changed', self._on_search_method_changed)

        # Setup Link buttons
        self.btlWidget = Gtk.LinkButton.new_with_label(label='Widget', uri='https://docs.gtk.org/gtk4/class.Widget.html') # Widget Link button
        self.btlMethod = Gtk.LinkButton() # Method Link button

        # Setup main window
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, hexpand=True, vexpand=False)
        box.props.margin_start = 12
        box.props.margin_end = 12
        box.props.margin_top = 6
        box.props.margin_bottom = 6
        boxDD = Gtk.Box(spacing=12, hexpand=True, vexpand=False)
        boxDD.set_homogeneous(True)
        boxDD.append(self.ddwdg)
        boxDD.append(self.ddmth)
        boxLB = Gtk.Box(spacing=12, hexpand=True, vexpand=False)
        boxLB.set_homogeneous(True)
        boxLB.append(self.btlWidget)
        boxLB.append(self.btlMethod)
        box.append(boxDD)
        box.append(boxLB)
        self.set_child(box)

    def create_dropdown(self, model, factory):
        dropdown = Gtk.DropDown(model=model, factory=factory, hexpand=True)
        dropdown.set_enable_search(True)
        return dropdown

    def _get_search_entry_widget(self, dropdown):
        popover = dropdown.get_last_child()
        box = popover.get_child()
        box2 = box.get_first_child()
        search_entry = box2.get_first_child() # Gtk.SearchEntry
        return search_entry

    def _on_factory_widget_setup(self, factory, list_item):
        box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        label = Gtk.Label()
        box.append(label)
        list_item.set_child(box)

    def _on_factory_widget_bind(self, factory, list_item):
        box = list_item.get_child()
        label = box.get_first_child()
        widget = list_item.get_item()
        label.set_text(widget.name)

    def _on_factory_method_setup(self, factory, list_item):
        box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        label = Gtk.Label()
        box.append(label)
        list_item.set_child(box)

    def _on_factory_method_bind(self, factory, list_item):
        box = list_item.get_child()
        label = box.get_first_child()
        method = list_item.get_item()
        label.set_text(method.name)

    def _on_selected_widget(self, dropdown, data):
        widget = dropdown.get_selected_item()
        self.btlWidget.set_label(widget.name)
        self.btlWidget.set_uri('https://docs.gtk.org/gtk4/class.%s.html' % widget.name[4:])
        self.model_method.remove_all()

        name = widget.name
        obj = eval(name)
        a = set(dir(obj))
        b = set(dir(Gtk.Widget))
        c = a - b
        for item in sorted(list(c)):
            self.model_method.append(Method(name=item))

    def _on_selected_method(self, dropdown, data):
        widget = self.ddwdg.get_selected_item()
        method = dropdown.get_selected_item()
        if method is not None:
            self.btlMethod.set_label(method.name)
            if method.name.startswith('new'):
                self.btlMethod.set_uri('https://docs.gtk.org/gtk4/ctor.%s.%s.html' % (widget.name[4:], method.name))
            else:
                self.btlMethod.set_uri('https://docs.gtk.org/gtk4/method.%s.%s.html' % (widget.name[4:], method.name))

    def _on_search_method_changed(self, search_entry):
        self.search_text_method = search_entry.get_text()
        self.filter_method.changed(Gtk.FilterChange.DIFFERENT)

    def _on_search_widget_changed(self, search_entry):
        self.search_text_widget = search_entry.get_text()
        self.filter_widget.changed(Gtk.FilterChange.DIFFERENT)

    def _do_filter_widget_view(self, item, filter_list_model):
        if self.search_text_widget.upper() in item.name.upper():
            display = True
        else:
            display = False
        return display

    def _do_filter_method_view(self, item, filter_list_model):
        if self.search_text_method.upper() in item.name.upper():
            display = True
        else:
            display = False
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
