#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

import gi
gi.require_version('Adw', '1')
gi.require_version('GdkPixbuf', '2.0')
gi.require_version('Gtk', '4.0')

from gi.repository import Gtk, Adw
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Pango
from gi.repository.GdkPixbuf import Pixbuf

from MiAZ.backend.log import get_logger
from MiAZ.backend.models import Country
from MiAZ.frontend.desktop.icons import MiAZIconManager

# ~ class HeaderType:
    # ~ DEFAULT = 1
    # ~ ARTIST = 2
    # ~ ALBUM = 3
    # ~ ROUNDED = 4

class MiAZFactory:
    def __init__(self, app):
        self.app = app
        self.log = get_logger('MiAZFactory')

    def create_actionrow(self, icon_name:str = '', title:str = '', subtitle:str = '', prefix: Gtk.Widget = None, suffix: Gtk.Widget = None):
        row = Adw.ActionRow.new()
        if len(icon_name) > 0:
            row.set_icon_name(icon_name)

        row.set_title(title)

        if len(subtitle) > 0:
            row.set_subtitle(subtitle)

        if prefix is not None:
            prefix.set_valign(Gtk.Align.CENTER)
            row.add_prefix(prefix)

        if suffix is not None:
            suffix.set_valign(Gtk.Align.CENTER)
            row.add_suffix(suffix)

        return row

    def create_box_filter(self, title, widget: Gtk.Widget) -> Gtk.Box:
        box = Gtk.Box.new(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        box.set_margin_bottom(margin=12)
        # ~ box.set_homogeneous(True)
        # ~ vbox.get_style_context().add_class(class_name='frame')
        lblTitle = self.create_label('<small>%s</small>' % title)
        lblTitle.set_xalign(0.0)
        box.append(lblTitle)
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

    def create_button(self, icon_name='', title='', callback=None, width=32, height=32, css_classes=[], data=None):
        if len(icon_name.strip()) == 0:
            button = Gtk.Button(css_classes=css_classes)
            label = Gtk.Label()
            label.set_markup(title)
            button.set_child(label)
            button.set_valign(Gtk.Align.CENTER)
        else:
            button = Gtk.Button(
                css_classes=css_classes,
                child=Adw.ButtonContent(
                    label=title,
                    icon_name=icon_name
                    )
                )
        # ~ button.set_has_frame(False)
        if callback is not None:
            button.connect('clicked', callback, data)
        return button

    def create_button_toggle(self, icon_name: str = '', title: str = '', callback=None, css_classes=[], data=None) -> Gtk.ToggleButton:
        if len(icon_name.strip()) == 0:
            button = Gtk.ToggleButton(css_classes=css_classes)
            button.set_label(title)
            button.set_valign(Gtk.Align.CENTER)
        else:
            button = Gtk.ToggleButton(
                css_classes=css_classes,
                child=Adw.ButtonContent(
                    label=title,
                    icon_name=icon_name
                    )
                )
        button.set_has_frame(False)
        if callback is None:
            button.connect('toggled', self.noop, data)
        else:
            button.connect('toggled', callback, data)
        return button

    def create_button_check(self, title: str = '', active: bool = False, callback=None) -> Gtk.CheckButton:
        button = Gtk.CheckButton.new_with_label(title)
        button.set_active(active)
        if callback is not None:
            button.connect('toggled', callback)
        return button

    def create_button_menu(self, xml: str = '', name:str = '', child: Gtk.Widget = None, css_classes: list = []):
        """
        Gtk.Menubutton with a menu defined in a Gtk.Builder xml string
        """
        button = Gtk.MenuButton(child=child, css_classes=css_classes)
        builder = Gtk.Builder()
        builder.add_from_string(xml)
        menu = builder.get_object(name)
        button.set_menu_model(menu)
        return button

    def create_button_popover(self, icon_name: str = '', css_classes: list = [], widgets: list = []) -> Gtk.MenuButton:
        listbox = Gtk.ListBox.new()
        listbox.set_activate_on_single_click(False)
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        for widget in widgets:
            listbox.append(child=widget)
        vbox = self.create_box_vertical()
        vbox.append(child=listbox)
        popover = Gtk.Popover()
        popover.set_child(vbox)
        popover.present()
        button = Gtk.MenuButton(child=Adw.ButtonContent(icon_name=icon_name, css_classes=css_classes))
        button.set_popover(popover)
        return button


    def create_dropdown_generic(self, item_type, ellipsize=True):
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
            label.set_text(item.title)

        def _on_search_changed(search_entry, item_filter):
            text = search_entry.get_text()
            item_filter.changed(Gtk.FilterChange.DIFFERENT)

        def _do_filter(item, filter_list_model, search_entry):
            text = search_entry.get_text()
            name = '%s %s' % (item.id, item.title)
            return text.upper() in name.upper()

        def _get_search_entry_widget(dropdown):
            popover = dropdown.get_last_child()
            box = popover.get_child()
            box2 = box.get_first_child()
            search_entry = box2.get_first_child() # Gtk.SearchEntry
            return search_entry

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
        dropdown.set_enable_search(True)
        search_entry = _get_search_entry_widget(dropdown)
        item_filter = Gtk.CustomFilter.new(_do_filter, filter_model, search_entry)
        filter_model.set_filter(item_filter)
        search_entry.connect('search-changed', _on_search_changed, item_filter)

        return dropdown

    def create_dialog(self, parent, title, widget, width=-1, height=-1):
        dialog = Gtk.Dialog()
        dlgHeader = Gtk.HeaderBar()
        dialog.set_titlebar(dlgHeader)
        dialog.set_modal(True)
        dialog.set_title(title)
        if width != -1 and height != -1:
            dialog.set_size_request(width, height)
        dialog.set_transient_for(parent)
        contents = dialog.get_content_area()
        contents.set_margin_top(margin=12)
        contents.set_margin_end(margin=12)
        contents.set_margin_bottom(margin=12)
        contents.set_margin_start(margin=12)
        contents.append(widget)
        return dialog

    def create_dialog_question(self, parent, title, body, width=-1, height=-1):
        dialog = self.create_dialog(parent, title, body, width, height)
        dialog.add_buttons('Cancel', Gtk.ResponseType.CANCEL, 'Accept', Gtk.ResponseType.ACCEPT)
        dialog.set_default_response(Gtk.ResponseType.CANCEL)
        btnCancel = dialog.get_widget_for_response(Gtk.ResponseType.CANCEL)
        btnCancel.get_style_context().add_class(class_name='destructive-action')
        btnAccept = dialog.get_widget_for_response(Gtk.ResponseType.ACCEPT)
        btnAccept.get_style_context().add_class(class_name='suggested-action')
        return dialog

    def create_filechooser(self, parent, title, target, callback, data=None):
        d_filechooser = Gtk.Dialog()
        d_filechooser.set_title(title)
        d_filechooser.set_transient_for(parent)
        d_filechooser.set_modal(True)
        d_filechooser.add_buttons('Cancel', Gtk.ResponseType.CANCEL, 'Accept', Gtk.ResponseType.ACCEPT)
        d_filechooser.connect('response', callback, data)
        contents = d_filechooser.get_content_area()
        box = self.create_box_vertical()
        w_filechooser = Gtk.FileChooserWidget()
        box.append(w_filechooser)
        if target == 'FOLDER':
            w_filechooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        elif target == 'FILE':
            w_filechooser.set_action(Gtk.FileChooserAction.OPEN)
        elif target == 'SAVE':
            w_filechooser.set_action(Gtk.FileChooserAction.SAVE)
        contents.append(box)
        return d_filechooser

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
        self.app.add_action(action)
        menuitem.set_detailed_action(detailed_action='app.%s' % name)
        return menuitem

    def create_row(self, filepath: str, filedict: dict) -> Gtk.Widget:
        row = Gtk.Frame()
        row.set_margin_top(margin=3)
        row.set_margin_end(margin=3)
        row.set_margin_bottom(margin=3)
        row.set_margin_start(margin=3)
        boxCenter = Gtk.CenterBox()
        boxCenter.set_margin_top(margin=6)
        boxCenter.set_margin_end(margin=6)
        boxCenter.set_margin_bottom(margin=6)
        boxCenter.set_margin_start(margin=6)
        icon_mime = self.app.icman.get_icon_mimetype_from_file(filepath, 32)
        btnMime = Gtk.Button(css_classes=['flat'])
        btnMime.set_child(icon_mime)
        btnMime.connect('clicked', self.noop)
        icon_flag = self.app.icman.get_flag('ES', 32)
        label = self.create_label(os.path.basename(filepath))
        boxLayout = Gtk.Box()
        boxLayout.set_margin_start(6)
        boxLayout.set_margin_end(6)
        boxLayout.append(label)
        boxCenter.set_start_widget(btnMime)
        boxCenter.set_center_widget(boxLayout)
        boxCenter.set_end_widget(icon_flag)
        row.set_child(boxCenter)
        return row

    def create_scrolledwindow(self):
        scrwin = Gtk.ScrolledWindow()
        scrwin.set_hexpand(True)
        scrwin.set_vexpand(True)
        return scrwin

    def create_view(self, customview, title):
        box = self.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
        label = self.create_label(title)
        # ~ frame = Gtk.Frame()
        view = customview(self.app)
        view.get_style_context().add_class(class_name='monospace')
        view.get_style_context().add_class(class_name='caption')
        view.set_hexpand(True)
        view.set_vexpand(True)
        # ~ frame.set_child(view)
        box.append(label)
        # ~ box.append(frame)
        return box, view


    def create_switch_button(self, icon_name, title, callback=None, data=None):
        button = Gtk.Switch()
        if callback is None:
            button.connect('notify::active', self.noop, data)
        else:
            button.connect('notify::active', callback, data)
        return button

    def noop(self, *args):
        self.log.debug(args)

    def create_menu_selection_single(self) -> Gio.Menu:
        self.menu_workspace_single = Gio.Menu.new()

        # Fake item for menu title
        item_fake = Gio.MenuItem.new()
        item_fake.set_label('Single selection')
        action = Gio.SimpleAction.new('fake', None)
        item_fake.set_detailed_action(detailed_action='fake')
        self.menu_workspace_single.append_item(item_fake)

        item_rename_manual = Gio.MenuItem.new()
        item_rename_manual.set_label('Rename manually')
        action = Gio.SimpleAction.new('rename_ws_manually', None)
        # ~ action.connect('activate', self.action_rename_manually)
        self.app.add_action(action)
        item_rename_manual.set_detailed_action(detailed_action='app.rename_ws_manually')
        self.menu_workspace_single.append_item(item_rename_manual)

        return self.menu_workspace_single

    def create_menu_selection_multiple(self):
        self.menu_workspace_multiple = Gio.Menu.new()

        fields = ['date', 'country', 'group', 'purpose']
        item_fake = Gio.MenuItem.new()
        item_fake.set_label('Multiple selection')
        action = Gio.SimpleAction.new('fake', None)
        item_fake.set_detailed_action(detailed_action='fake')
        self.menu_workspace_multiple.append_item(item_fake)

        # Submenu for mass renaming
        submenu_rename_root = Gio.Menu.new()
        submenu_rename = Gio.MenuItem.new_submenu(
            label='Mass renaming of...',
            submenu=submenu_rename_root,
        )
        self.menu_workspace_multiple.append_item(submenu_rename)

        for item in fields:
            menuitem = Gio.MenuItem.new()
            menuitem.set_label(label='... %s' % item)
            action = Gio.SimpleAction.new('rename_%s' % item, None)
            callback = 'self.action_rename'
            action.connect('activate', eval(callback), item)
            self.app.add_action(action)
            menuitem.set_detailed_action(detailed_action='app.rename_%s' % item)
            submenu_rename_root.append_item(menuitem)

        # Submenu for mass adding
        submenu_add_root = Gio.Menu.new()
        submenu_add = Gio.MenuItem.new_submenu(
            label='Mass adding of...',
            submenu=submenu_add_root,
        )
        self.menu_workspace_multiple.append_item(submenu_add)

        for item in fields:
            menuitem = Gio.MenuItem.new()
            menuitem.set_label(label='... %s' % item)
            action = Gio.SimpleAction.new('add_%s' % item, None)
            callback = 'self.action_add'
            action.connect('activate', eval(callback), item)
            self.app.add_action(action)
            menuitem.set_detailed_action(detailed_action='app.add_%s' % item)
            submenu_add_root.append_item(menuitem)

        item_force_update = Gio.MenuItem.new()
        item_force_update.set_label(label='Force update')
        action = Gio.SimpleAction.new('workspace_update', None)
        action.connect('activate', self.update)
        self.app.add_action(action)
        item_force_update.set_detailed_action(detailed_action='app.workspace_update')
        self.menu_workspace_multiple.append_item(item_force_update)

        item_delete = Gio.MenuItem.new()
        item_delete.set_label(label='Delete documents')
        action = Gio.SimpleAction.new('workspace_delete', None)
        action.connect('activate', self.noop)
        self.app.add_action(action)
        item_delete.set_detailed_action(detailed_action='app.workspace_delete')
        self.menu_workspace_multiple.append_item(item_delete)
        return self.menu_workspace_multiple

# ~ class MenuHeader(Gio.MenuItem):
    # ~ """
        # ~ A simple menu header with label and icon
    # ~ """

    # ~ def __init__(self, label, icon_name):
        # ~ """
            # ~ Init menu
            # ~ @param label as str
            # ~ @param icon_name as str
        # ~ """
        # ~ Gio.MenuItem.__init__(self)
        # ~ header_type = GLib.Variant("i", HeaderType.DEFAULT)
        # ~ vlabel = GLib.Variant("s", label)
        # ~ vicon_name = GLib.Variant("s", icon_name)
        # ~ header = [header_type, vlabel, vicon_name]
        # ~ self.set_attribute_value("header", GLib.Variant("av", header))
