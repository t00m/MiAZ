#!/usr/bin/python3
# File: factory.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Custom widgets widely used

from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import Gio
from gi.repository import Pango

from MiAZ.backend.log import MiAZLog
from MiAZ.frontend.desktop.widgets.button import MiAZPopoverButton
from MiAZ.frontend.desktop.widgets.filechooser import MiAZFileChooserDialog


def get_children(obj: Gtk.Widget) -> list[Gtk.Widget]:
    """
    Get list of widget's children
    """

    children: list[Gtk.Widget] = []
    child: Gtk.Widget = obj.get_first_child()
    while child:
        children.append(child)
        child = child.get_next_sibling()
    return children

from typing import Callable
from gi.repository import Gtk  # type:ignore

from MiAZ.frontend.desktop.services.factory import get_children


class MiAZBox(Gtk.Box):
    def __init__(self, children: list[Gtk.Widget], **kwargs) -> None:
        super().__init__(**kwargs)
        for child in children:
            self.append(child)

    @property
    def children(self) -> list[Gtk.Widget]:
        return get_children(self)

    def for_each(self, func: Callable) -> None:
        """Call func for each child. Child passed as first argument"""

        for child in self.children:
            func(child)



class MiAZFactory:
    def __init__(self, app):
        self.app = app
        self.log = MiAZLog('MiAZ.Factory')
        self.icons = self.app.get_service('icons')

    def get_children(obj: Gtk.Widget) -> list[Gtk.Widget]:
        """
        Get list of widget's children
        """

        children: list[Gtk.Widget] = []
        child: Gtk.Widget = obj.get_first_child()
        while child:
            children.append(child)
            child = child.get_next_sibling()
        return children

    def create_actionrow(self, title:str = '', subtitle:str = '', prefix: Gtk.Widget = None, suffix: Gtk.Widget = None):
        box = Gtk.CenterBox(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_hexpand(True)
        box.set_vexpand(True)
        row = Gtk.ListBoxRow.new()
        row.set_child(box)
        hprefix = self.create_box_horizontal(hexpand=False)
        hsuffix = self.create_box_horizontal(hexpand=False)
        box.set_start_widget(hprefix)
        box.set_end_widget(hsuffix)

        hbox = self.create_box_horizontal(hexpand=True)

        vbox = self.create_box_vertical(hexpand=True, vexpand=False)
        if len(title) > 0:
            lblTitle = Gtk.Label()
            lblTitle.set_markup(f"<b>{title}</b>")
            lblTitle.set_xalign(0.0)
            vbox.append(lblTitle)

        if len(subtitle) > 0:
            lblSubtitle = Gtk.Label()
            lblSubtitle.set_markup(f"<small>{subtitle}</small>")
            lblSubtitle.set_xalign(0.0)
            vbox.append(lblSubtitle)

        hbox.append(vbox)

        if prefix is not None:
            hprefix.append(prefix)
        hprefix.append(hbox)

        if suffix is not None:
            hsuffix.append(suffix)

        return row

    def create_box_filter(self, title, widget: Gtk.Widget) -> Gtk.Box:
        css = "frame.transparent-frame {\
                background-color: transparent; \
                border: none; \
            }"

        css_provider = Gtk.CssProvider()
        css_provider.load_from_string(css)
        # Apply the CSS to the default display
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        box = Gtk.Box.new(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        box.set_margin_bottom(margin=12)
        frame = Gtk.Frame()
        frame.set_name("transparent-frame")  # Set the CSS name
        frame.add_css_class("transparent-frame")  # Add the CSS class
        lblTitle = self.create_label(f"<small>{title}</small>")
        frame.set_label_widget(lblTitle)
        frame.set_child(widget)
        box.append(frame)
        # ~ lblTitle.set_xalign(0.0)
        # ~ box.append(lblTitle)
        # ~ widget.set_tooltip_text(title)
        box.append(widget)
        return box

    def create_box_horizontal(self, margin:int = 3, spacing:int = 3, hexpand: bool = False, vexpand: bool = False):
        box = Gtk.Box.new(orientation=Gtk.Orientation.HORIZONTAL, spacing=spacing)
        box.set_margin_top(margin=margin)
        box.set_margin_end(margin=margin)
        box.set_margin_bottom(margin=margin)
        box.set_margin_start(margin=margin)
        box.set_hexpand(hexpand)
        box.set_vexpand(vexpand)
        return box

    def create_box_vertical(self, margin:int = 3, spacing:int = 3, hexpand: bool = False, vexpand: bool = False):
        box = Gtk.Box.new(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)
        box.set_margin_top(margin=margin)
        box.set_margin_end(margin=margin)
        box.set_margin_bottom(margin=margin)
        box.set_margin_start(margin=margin)
        box.set_hexpand(hexpand)
        box.set_vexpand(vexpand)
        return box

    def create_button_content(self, icon_name='', title='', callback=None, size=16, css_classes=[''], data=None):
        hbox = self.create_box_horizontal(spacing=0, margin=0, hexpand=False, vexpand=False)
        if len(icon_name.strip()) > 0:
            icon = self.icons.get_image_by_name(icon_name, size=size)
            icon.set_pixel_size(size)
            icon.set_valign(Gtk.Align.CENTER)
            hbox.append(icon)

        if len(title) > 0:
            label = Gtk.Label()
            label.set_markup(title)
            label.set_valign(Gtk.Align.CENTER)
            hbox.append(label)

        for css_class in css_classes:
            hbox.get_style_context().add_class(class_name=css_class)

        return hbox

    def create_button(self, icon_name='', title='', tooltip='', callback=None, size=16, css_classes=None, data=None):
        if css_classes is None:
            css_classes = []
        button = Gtk.Button(css_classes=css_classes)
        hbox = self.create_box_horizontal(spacing=6, margin=0)
        if len(icon_name.strip()) > 0:
            icon = self.icons.get_image_by_name(icon_name)
            icon.set_pixel_size(size)
            icon.set_valign(Gtk.Align.CENTER)
            hbox.append(icon)

        if len(title) > 0:
            label = Gtk.Label()
            label.set_markup(title)
            label.set_valign(Gtk.Align.CENTER)
            hbox.append(label)

        if len(tooltip) > 0:
            button.set_tooltip_markup(tooltip)

        button.set_child(hbox)

        if callback is not None:
            button.connect('clicked', callback, data)

        return button

    def create_button_toggle(self, icon_name: str = '', title: str = '', tooltip: str = '', callback=None, css_classes=None, data=None) -> Gtk.ToggleButton:
        if css_classes is None:
            css_classes = []
        button = Gtk.ToggleButton(css_classes=css_classes)
        hbox = self.create_box_horizontal(spacing=3, margin=0)
        if len(icon_name.strip()) == 0:
            icon = Gtk.Image()
        else:
            icon = self.icons.get_image_by_name(icon_name)

        label = Gtk.Label()
        if len(title) > 0:
            label.set_markup(title)

        if len(tooltip) > 0:
            button.set_tooltip_markup(tooltip)

        hbox.append(icon)
        hbox.append(label)
        button.set_child(hbox)
        button.set_valign(Gtk.Align.CENTER)
        button.set_has_frame(False)
        if callback is not None:
            button.connect('toggled', callback, data)
        return button

    def create_button_switch(self, title: str = '', active: bool = False, callback=None) -> Gtk.CheckButton:
        button = Gtk.Switch()
        button.set_active(active)
        if callback is not None:
            button.connect('activate', callback)
        return button

    def create_button_check(self, title: str = '', active: bool = False, callback=None) -> Gtk.CheckButton:
        button = Gtk.CheckButton()
        button.set_active(active)
        if callback is not None:
            button.connect('activate', callback)
        return button

    def create_button_menu(self, icon_name: str = '', title:str = '', css_classes: list = None, menu: Gio.Menu = None)-> Gtk.MenuButton:
        if css_classes is None:
            css_classes = []
        child=self.create_button_content(icon_name=icon_name, title=title, css_classes=css_classes)
        button = Gtk.MenuButton()
        button.set_child(child)
        popover = Gtk.PopoverMenu.new_from_model(menu)
        button.set_popover(popover=popover)
        button.set_sensitive(True)
        return button

    def create_button_popover(self, icon_name: str = '', title: str = '', css_classes: list = [], widgets: list = []) -> Gtk.MenuButton:
        return MiAZPopoverButton(self.app, icon_name=icon_name, title=title, css_classes=css_classes, widgets=widgets)

    def create_dropdown_generic(self, item_type, ellipsize=True, enable_search=True):
        def _get_search_entry_widget(dropdown):
            popover = dropdown.get_last_child()
            box = popover.get_child()
            box2 = box.get_first_child()
            search_entry = box2.get_first_child() # Gtk.SearchEntry
            return search_entry

        def _on_search_widget_changed(search_entry):
            pass

        def _on_factory_setup(factory, list_item, ellipsize):
            box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
            label = Gtk.Label()
            if ellipsize:
                label.set_property('ellipsize', Pango.EllipsizeMode.MIDDLE)
            box.append(label)
            list_item.set_child(box)

        def _on_factory_bind(factory, list_item):
            box = list_item.get_child()
            label = box.get_last_child()
            item = list_item.get_item()
            label.set_markup(f'{item.title}')
            label.get_style_context().add_class(class_name='caption')
            label.get_style_context().add_class(class_name='monospace')

        def _on_search_changed(search_entry, item_filter):
            item_filter.changed(Gtk.FilterChange.DIFFERENT)

        def _do_filter(item, filter_list_model, search_entry):
            text = search_entry.get_text()
            name = f'{item.id} {item.title}'
            return text.upper() in name.upper()

        def _clear_dropdown(button, dropdown):
            # ~ model = dropdown.get_model()
            dropdown.set_selected(0)

        # Set up the factory
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", _on_factory_setup, ellipsize)
        factory.connect("bind", _on_factory_bind)

        # Create the model
        model = Gio.ListStore(item_type=item_type)
        sort_model  = Gtk.SortListModel(model=model) # FIXME: Gtk.Sorter?
        filter_model = Gtk.FilterListModel(model=sort_model)

        # Create dropdown
        dropdown = Gtk.DropDown(model=filter_model, factory=factory, hexpand=True)
        dropdown.set_show_arrow(True)

        # Enable search
        dropdown.set_enable_search(enable_search)
        search_entry = _get_search_entry_widget(dropdown)
        item_filter = Gtk.CustomFilter.new(_do_filter, filter_model, search_entry)
        filter_model.set_filter(item_filter)
        search_entry.connect('search-changed', _on_search_changed, item_filter)

        # Enable clear button by brute force
        box = search_entry.get_parent()
        button = self.create_button(icon_name='io.github.t00m.MiAZ-entry_clear', css_classes=['flat'], tooltip='Clear this filter', callback=_clear_dropdown, data=dropdown)
        button.set_margin_start(3)
        box.append(button)

        # Enable placeholder text by brute force too...
        # 'set_placeholder_text' doesn't work with lower Gtk4 versions
        # ~ search_entry.set_placeholder_text("Type %s" % item_type.__title__)
        image = search_entry.get_first_child()
        text_widget = image.get_next_sibling()
        text_widget.set_placeholder_text(f"Type {item_type.__title__}")
        # Enable context menu
        # FIXME: This code insert a new entry in the context menu
        # Apparently, it works. But it doesn't. It always chooses
        # the last dropdown created ¿?
        # ~ menu_dropdown = Gio.Menu.new()
        # ~ text_widget.set_extra_menu(menu_dropdown)
        # ~ menuitem = self.create_menuitem(name='clear', label='Clear dropdown', callback=_clear_dropdown, data=dropdown, shortcuts=[])
        # ~ menu_dropdown.append_item(menuitem)

        return dropdown

    def create_filechooser(self, enable_response, title, target, callback, data=None):
        return MiAZFileChooserDialog(self.app, enable_response, title, target, callback, data)

    def create_frame(self, title:str = None, margin: int = 3, hexpand: bool = False, vexpand: bool = False) -> Gtk.Frame:
        frame = Gtk.Frame()
        frame.set_margin_top(margin)
        frame.set_margin_end(margin)
        frame.set_margin_bottom(margin)
        frame.set_margin_start(margin)
        frame.set_hexpand(hexpand)
        frame.set_vexpand(vexpand)
        if title is not None:
            label = self.create_label(title)
            frame.set_label_widget(label)
            frame.set_label_align(0.5)
        return frame

    def create_label(self, text: str = None) -> Gtk.Label:
        label = Gtk.Label()
        label.set_property('ellipsize', Pango.EllipsizeMode.MIDDLE)
        if text is not None:
            label.set_markup(text)
        return label

    def create_menu_action(self, name, callback, shortcuts=None):
        action = Gio.SimpleAction.new(name, None)
        action.connect('activate', callback)
        self.app.add_action(action)
        if shortcuts:
            self.app.set_accels_for_action(f'app.{name}', shortcuts)

    def create_menuitem(self, name, label, callback, data, shortcuts):
        menuitem = Gio.MenuItem.new()
        menuitem.set_label(label=label)
        action = Gio.SimpleAction.new(name, None)
        action.connect('activate', callback, data)
        action.set_enabled(True)
        self.app.add_action(action)
        menuitem.set_detailed_action(detailed_action=f'app.{name}')
        if shortcuts:
            self.app.set_accels_for_action(f'app.{name}', shortcuts)
        return menuitem

    def create_notebook_label(self, icon_name: str, title: str) -> Gtk.Widget:
        hbox = self.create_box_horizontal()
        icon = self.icons.get_image_by_name(icon_name)
        label = Gtk.Label()
        label.set_markup(f'<b>{title}</b>')
        hbox.append(icon)
        hbox.append(label)
        return hbox

    def create_scrolledwindow(self):
        scrwin = Gtk.ScrolledWindow()
        scrwin.set_hexpand(True)
        scrwin.set_vexpand(True)
        return scrwin

    def create_view(self, customview: Gtk.Widget, title=''):
        box = self.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
        view = customview(self.app)
        view.get_style_context().add_class(class_name='monospace')
        view.get_style_context().add_class(class_name='caption')
        view.set_hexpand(True)
        view.set_vexpand(True)
        if len(title) > 0:
            label = self.create_label(title)
            box.append(label)
        return box, view

    def create_switch_button(self, icon_name, title, callback=None, data=None):
        button = Gtk.Switch()
        if callback is not None:
            button.connect('notify::active', callback, data)
        return button

    def noop(self, *args):
        self.log.debug(args)
