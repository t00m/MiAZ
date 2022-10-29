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

class MiAZFactory:
    def __init__(self, app):
        self.app = app
        self.log = get_logger('MiAZFactory')

    def create_action(self, name, callback):
        """ Add an Action and connect to a callback """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.app.add_action(action)

    def create_box_filter(self, title: str, widget: Gtk.Widget) -> Gtk.Box:
        box = Gtk.Box.new(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        box.set_margin_bottom(margin=12)
        # ~ vbox.get_style_context().add_class(class_name='frame')
        lblTitle = self.create_label('<small>%s</small>' % title)
        lblTitle.set_xalign(0.0)
        box.append(lblTitle)
        box.append(widget)
        return box

    def create_button(self, icon_name, title, callback=None, width=32, height=32, css_classes=['flat'], data=None):
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
        # ~ button.get_style_context().add_class(class_name='success')
        button.set_has_frame(True)
        if callback is None:
            button.connect('clicked', self.noop, data)
        else:
            button.connect('clicked', callback, data)
        return button

    def create_button_toggle(self, icon_name: str, title: str, callback=None, css_classes=['circular'], data=None) -> Gtk.ToggleButton:
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
        button.set_has_frame(True)
        if callback is None:
            button.connect('toggled', self.noop, data)
        else:
            button.connect('toggled', callback, data)
        return button

        # ~ button = Gtk.ToggleButton()
        # ~ btnFileSelect = Gtk.ToggleButton()
        # ~ btnFileSelect.connect('toggled', self.on_selected_rows_changed)
        # ~ btnFileSelect.set_icon_name('miaz-edit')
        # ~ btnFileSelect.set_valign(Gtk.Align.CENTER)
        # ~ btnFileSelect.set_hexpand(False)

    def create_combobox_countries(self):
        model = Gtk.ListStore(str, str, Pixbuf)
        icon = self.app.icman.get_flag_pixbuf('__')
        first = model.append(['All countries', '', icon])
        ucodes = self.app.get_config('countries').load()
        gcodes = self.app.get_config('countries').load_global()
        for code in ucodes:
            icon = self.app.icman.get_flag_pixbuf(code)
            name = gcodes[code]
            model.append([name, code, icon])

        cmbCountries = Gtk.ComboBox.new_with_model(model)
        cmbCountries.set_active_iter(first)

        renderer = Gtk.CellRendererText()
        cmbCountries.pack_start(renderer, True)
        cmbCountries.add_attribute(renderer, "markup", 0)

        renderer = Gtk.CellRendererText()
        renderer.set_visible(False)
        cmbCountries.pack_start(renderer, True)
        cmbCountries.add_attribute(renderer, "text", 1)

        renderer = Gtk.CellRendererPixbuf()
        cmbCountries.pack_start(renderer, False)
        cmbCountries.add_attribute(renderer, "pixbuf", 2)

        return cmbCountries

    def create_dropdown_countries(self):
        def _on_factory_setup(factory, list_item):
            box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
            image = Gtk.Image()
            label = Gtk.Label()
            box.append(image)
            box.append(label)
            list_item.set_child(box)

        def _on_factory_bind(factory, list_item):
            box = list_item.get_child()
            image = box.get_first_child()
            label = box.get_last_child()
            country = list_item.get_item()
            label.set_text(country.country_name)
            country_flag = self.app.icman.get_flag_pixbuf(country.country_id)
            image.set_from_pixbuf(country_flag)
            image.set_pixel_size(28)

        # Populate the model
        self.model = Gio.ListStore(item_type=Country)
        lcountries = self.app.get_config('countries').load()
        gcountries = self.app.get_config('countries').load_global()
        self.model.append(Country(country_id='__', country_name='All countries'))
        for code in lcountries:
            self.model.append(Country(country_id=code, country_name=gcountries[code]))

        # Set up the factory
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", _on_factory_setup)
        factory.connect("bind", _on_factory_bind)

        return Gtk.DropDown(model=self.model, factory=factory, hexpand=True)

    def create_dropdown_generic(self, item_type, conf):

        def _on_factory_setup(factory, list_item):
            box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
            label = Gtk.Label()
            box.append(label)
            list_item.set_child(box)

        def _on_factory_bind(factory, list_item):
            box = list_item.get_child()
            label = box.get_last_child()
            item = list_item.get_item()
            label.set_text(item.name)

        # Populate the model
        self.model = Gio.ListStore(item_type=item_type)
        values = self.app.get_config(conf).load()
        for value in values:
            self.model.append(item_type(name=value))

        # Set up the factory
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", _on_factory_setup)
        factory.connect("bind", _on_factory_bind)

        return Gtk.DropDown(model=self.model, factory=factory, hexpand=True)

    def create_combobox_text(self, conf: str) -> Gtk.ComboBox:
        model = Gtk.ListStore(str, str)
        combobox = Gtk.ComboBox()
        combobox.set_model(model)
        # ~ combobox.set_entry_text_column(0)

        renderer = Gtk.CellRendererText()
        renderer.set_visible(False)
        combobox.pack_start(renderer, True)
        combobox.add_attribute(renderer, "text", 0)

        renderer = Gtk.CellRendererText()
        combobox.pack_start(renderer, False)
        combobox.add_attribute(renderer, "markup", 1)

        first = model.append(['', 'All %s' % conf])
        items = self.app.get_config(conf).load()
        for key in items:
            model.append([key, key.title()])
        combobox.set_active_iter(first)
        return combobox

    def create_combobox_text_from(self) -> Gtk.ComboBox:
        model = Gtk.ListStore(str, str)
        combobox = Gtk.ComboBox()
        combobox.set_model(model)

        renderer = Gtk.CellRendererText()
        renderer.set_visible(False)
        combobox.pack_start(renderer, True)
        combobox.add_attribute(renderer, "text", 0)

        renderer = Gtk.CellRendererText()
        combobox.pack_start(renderer, False)
        combobox.add_attribute(renderer, "markup", 1)

        first = model.append(['', 'From all'])
        items = self.app.get_config('organizations').load()
        for key in items:
            model.append([key, items[key]])
        combobox.set_active_iter(first)
        return combobox

    def create_combobox_text_to(self) -> Gtk.ComboBox:
        model = Gtk.ListStore(str, str)
        combobox = Gtk.ComboBox()
        combobox.set_model(model)

        renderer = Gtk.CellRendererText()
        renderer.set_visible(False)
        combobox.pack_start(renderer, True)
        combobox.add_attribute(renderer, "text", 0)

        renderer = Gtk.CellRendererText()
        combobox.pack_start(renderer, False)
        combobox.add_attribute(renderer, "markup", 1)

        first = model.append(['', 'To all'])
        items = self.app.get_config('organizations').load()
        for key in items:
            model.append([key, items[key]])
        combobox.set_active_iter(first)
        return combobox

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
        dialog.add_buttons('No', Gtk.ResponseType.NO, 'Yes', Gtk.ResponseType.YES)
        dialog.set_default_response(Gtk.ResponseType.YES)
        btnYes = dialog.get_widget_for_response(Gtk.ResponseType.YES)
        btnYes.get_style_context().add_class(class_name='suggested-action')
        btnNo = dialog.get_widget_for_response(Gtk.ResponseType.NO)
        btnNo.get_style_context().add_class(class_name='destructive-action')
        return dialog

    def create_label(self, text: str) -> Gtk.Label:
        label = Gtk.Label()
        label.set_markup(text)
        label.set_property('ellipsize', Pango.EllipsizeMode.MIDDLE)
        return label

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
        # ~ boxCenter.set_hexpand(True)
        # ~ boxCenter.set_vexpand(True)
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


    def create_switch_button(self, icon_name, title, callback=None, data=None):
        button = Gtk.Switch()
        if callback is None:
            button.connect('notify::active', self.noop, data)
        else:
            button.connect('notify::active', callback, data)
        return button

    def create_treeview_column_icon(self, name: str, col_id: int, visible: bool, expand: bool, clickable: bool, indicator: bool, sort_col: int):
        renderer = Gtk.CellRendererPixbuf()
        column = Gtk.TreeViewColumn(name, renderer, pixbuf=col_id)
        renderer.set_alignment(0.0, 0.5)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(expand)
        column.set_visible(visible)
        column.set_clickable(clickable)
        column.set_sort_indicator(indicator)
        column.set_sort_column_id(sort_col)
        column.set_sort_order(Gtk.SortType.ASCENDING)
        return column

    def create_treeview_column_text(self, name: str, col_id: int, visible: bool, expand: bool, clickable: bool, indicator: bool, sort_col: int):
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(name, renderer, markup=col_id)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(expand)
        column.set_visible(visible)
        column.set_clickable(clickable)
        column.set_sort_indicator(indicator)
        column.set_sort_column_id(sort_col)
        column.set_sort_order(Gtk.SortType.ASCENDING)
        return column

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

        fields = ['date', 'country', 'collection', 'purpose']
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
