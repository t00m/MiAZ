# File: button.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Custom popover button

from gi.repository import Gtk


class MiAZPopoverButton(Gtk.MenuButton):
    """Menu button that opens a popover holding a list of action widgets.

    It subclasses Gtk.MenuButton instead of wrapping one inside a Gtk.Box so
    that it is a real button. A wrapping box is not a button, so the Adwaita
    '.linked' style skips it and the button renders detached from its toolbar
    siblings. As a direct button it links with them as expected.
    """
    def __init__(self, app, icon_name: str = '', title: str = '', css_classes: list = None, widgets: list = None):
        super().__init__()
        css_classes = css_classes if css_classes is not None else []
        widgets = widgets if widgets is not None else []
        self.app = app
        self.factory = self.app.get_service('factory')
        self.icon_name = icon_name
        self.title = title
        self.css_classes = css_classes
        self.widgets = widgets
        self.build_ui()

    def build_ui(self):
        self.listbox = Gtk.ListBox.new()
        self.listbox.set_activate_on_single_click(True)
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        for widget in self.widgets:
            self.listbox.append(child=widget)
        vbox = self.factory.create_box_vertical(spacing=0, margin=0, hexpand=True, vexpand=True)
        vbox.append(child=self.listbox)
        self.popover = Gtk.Popover()
        self.popover.set_child(vbox)
        self.set_child(self.factory.create_button_content(icon_name=self.icon_name, title=self.title))
        for css_class in self.css_classes:
            self.add_css_class(css_class)
        self.set_popover(self.popover)

    def add_widget(self, widget: Gtk.Widget):
        self.listbox.append(child=widget)

    def remove_widget(self, widget: Gtk.Widget):
        self.listbox.remove(child=widget)

