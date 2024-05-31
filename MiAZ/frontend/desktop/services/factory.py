#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: factory.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Custom widgets widely used
"""

from gi.repository import Gtk
from gi.repository import Gio
from gi.repository import Pango

from MiAZ.backend.log import get_logger
from MiAZ.frontend.desktop.widgets.button import MiAZPopoverButton
from MiAZ.frontend.desktop.widgets.filechooser import MiAZFileChooserDialog

class MiAZFactory:
    def __init__(self, app):
        self.app = app
        self.log = get_logger('MiAZ.Factory')
        self.icons = self.app.get_service('icons')

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
            lblTitle.set_markup("<b>%s</b>" % title)
            lblTitle.set_xalign(0.0)
            vbox.append(lblTitle)

        if len(subtitle) > 0:
            lblSubtitle = Gtk.Label()
            lblSubtitle.set_markup("<small>%s</small>" % subtitle)
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
        box = Gtk.Box.new(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        box.set_margin_bottom(margin=12)
        lblTitle = self.create_label('<b>%s</b>' % title)
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

    def create_button_content(self, icon_name='', title='', callback=None, width=16, height=16, css_classes=[''], data=None):
        hbox = self.create_box_horizontal(spacing=0, margin=0, hexpand=False, vexpand=False)
        if len(icon_name.strip()) > 0:
            icon = self.icons.get_image_by_name(icon_name, width=width, height=height)
            icon.set_pixel_size(width)
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

    def create_button(self, icon_name='', title='', tooltip='', callback=None, width=16, height=16, css_classes=[], data=None):
        button = Gtk.Button(css_classes=css_classes)

        # ~ button.get_style_context().add_class(class_name='flat')
        hbox = self.create_box_horizontal(spacing=0, margin=0)
        if len(icon_name.strip()) > 0:
            icon = self.icons.get_image_by_name(icon_name)
            icon.set_pixel_size(width)
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

    def create_button_toggle(self, icon_name: str = '', title: str = '', callback=None, css_classes=[], data=None) -> Gtk.ToggleButton:
        button = Gtk.ToggleButton(css_classes=css_classes)
        hbox = self.create_box_horizontal(spacing=0, margin=0)
        if len(icon_name.strip()) == 0:
            icon = Gtk.Image()
        else:
            icon = self.icons.get_image_by_name(icon_name)

        label = Gtk.Label()
        if len(title) > 0:
            label.set_markup(title)

        hbox.append(icon)
        hbox.append(label)
        button.set_child(hbox)
        button.set_valign(Gtk.Align.CENTER)
        button.set_has_frame(False)
        if callback is not None:
            button.connect('toggled', callback, data)
        return button

    def create_button_check(self, title: str = '', active: bool = False, callback=None) -> Gtk.CheckButton:
        button = Gtk.CheckButton.new_with_label(title)
        # ~ button.get_style_context().add_class(class_name='flat')
        button.set_active(active)
        if callback is not None:
            button.connect('toggled', callback)
        return button

    def create_button_menu(self, icon_name: str = '', title:str = '', css_classes: list = [], menu: Gio.Menu = None)-> Gtk.MenuButton:
        """Gtk.Menubutton with a menu"""
        child=self.create_button_content(icon_name=icon_name, title=title, css_classes=css_classes)
        button = Gtk.MenuButton()
        # ~ button.get_style_context().add_class(class_name='flat')
        button.set_child(child)
        popover = Gtk.PopoverMenu.new_from_model(menu)
        button.set_popover(popover=popover)
        button.set_sensitive(True)
        return button

    def create_button_popover(self, icon_name: str = '', title: str = '', css_classes: list = [], widgets: list = []) -> Gtk.MenuButton:
        return MiAZPopoverButton(self.app, icon_name=icon_name, title=title, css_classes=css_classes, widgets=widgets)
        # ~ listbox = Gtk.ListBox.new()
        # ~ listbox.set_activate_on_single_click(True)
        # ~ listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        # ~ for widget in widgets:
            # ~ listbox.append(child=widget)
        # ~ vbox = self.create_box_vertical(hexpand=False, vexpand=False)
        # ~ vbox.append(child=listbox)
        # ~ popover = Gtk.Popover()
        # ~ popover.set_child(vbox)
        # ~ popover.present()
        # ~ button = Gtk.MenuButton(child=self.create_button_content(icon_name=icon_name, title=title, css_classes=css_classes))
        # ~ button.set_popover(popover)
        # ~ return button

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
            label.set_markup('%s' % item.title)

        def _on_search_changed(search_entry, item_filter):
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

        # ~ def _clear_dropdown(self, nothing, dropdown):
            # ~ model = dropdown.get_model()
            # ~ print(len(model))
            # ~ dropdown.set_selected(0)
            # ~ print(dropdown)

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

        # Enable context menu
        # FIXME: This code insert a new entry in the context menu
        # Apparently, it works. But it doesn't. It always chooses
        # the last dropdown created ¿?
        # ~ image = search_entry.get_first_child()
        # ~ text_widget = image.get_next_sibling()
        # ~ menu_dropdown = Gio.Menu.new()
        # ~ text_widget.set_extra_menu(menu_dropdown)
        # ~ menuitem = self.create_menuitem(name='clear', label='Clear dropdown', callback=_clear_dropdown, data=dropdown, shortcuts=[])
        # ~ menu_dropdown.append_item(menuitem)

        return dropdown

    def create_dialog(self, parent, title, widget, width=-1, height=-1):
        dialog = Gtk.Dialog()
        dlgHeader = Gtk.HeaderBar()
        dialog.set_titlebar(dlgHeader)
        dialog.set_modal(True)
        dialog.set_title(title)
        # ~ dialog.set_margin_top(margin=12)
        # ~ dialog.set_margin_end(margin=12)
        # ~ dialog.set_margin_bottom(margin=12)
        # ~ dialog.set_margin_start(margin=12)
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
        btnCancel.set_margin_end(margin=12)
        btnCancel.set_margin_bottom(margin=12)
        btnAccept = dialog.get_widget_for_response(Gtk.ResponseType.ACCEPT)
        btnAccept.get_style_context().add_class(class_name='suggested-action')
        btnAccept.set_margin_end(margin=12)
        btnAccept.set_margin_bottom(margin=12)
        return dialog

    def create_filechooser(self, parent, title, target, callback, data=None):
        return MiAZFileChooserDialog(self.app, parent, title, target, callback, data)
        # FIXME: Gtk.FileChooser is deprecated. Use Gtk.FileDialog
        # FIXME: Available since Gtk 4.10: https://docs.gtk.org/gtk4/class.FileDialog.html
        # FIXME: However, Debian 12.5 is still in 4.8.3
        # FIXME: Choosing Gtk.FileChooser for compatibility
        # ~ d_filechooser = Gtk.Dialog()
        # ~ d_filechooser.set_title(title)
        # ~ d_filechooser.set_transient_for(parent)
        # ~ d_filechooser.set_modal(True)
        # ~ d_filechooser.add_buttons(_('Cancel'), Gtk.ResponseType.CANCEL, _('Accept'), Gtk.ResponseType.ACCEPT)
        # ~ btnCancel = d_filechooser.get_widget_for_response(Gtk.ResponseType.CANCEL)
        # ~ btnCancel.get_style_context ().add_class ('destructive-action')
        # ~ btnAccept = d_filechooser.get_widget_for_response(Gtk.ResponseType.ACCEPT)
        # ~ btnAccept.get_style_context ().add_class ('suggested-action')
        # ~ action_box = btnCancel.get_ancestor(Gtk.Box)
        # ~ action_box.set_spacing(6)
        # ~ action_box.set_margin_start(6)
        # ~ action_box.set_margin_end(6)
        # ~ action_box.set_margin_top(6)
        # ~ action_box.set_margin_bottom(6)

        # ~ d_filechooser.connect('response', callback, data)
        # ~ contents = d_filechooser.get_content_area()
        # ~ box = self.create_box_vertical()
        # ~ w_filechooser = Gtk.FileChooserWidget()
        # ~ box.append(w_filechooser)
        # ~ if target == 'FOLDER':
            # ~ w_filechooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        # ~ elif target == 'FILE':
            # ~ w_filechooser.set_action(Gtk.FileChooserAction.OPEN)
        # ~ elif target == 'SAVE':
            # ~ w_filechooser.set_action(Gtk.FileChooserAction.SAVE)
        # ~ contents.append(box)
        # ~ return d_filechooser

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
        if shortcuts:
            self.app.set_accels_for_action(f'app.{name}', shortcuts)
        return menuitem

    def create_notebook_label(self, icon_name: str, title: str) -> Gtk.Widget:
        hbox = self.create_box_horizontal()
        icon = self.icons.get_image_by_name(icon_name)
        label = Gtk.Label()
        label.set_markup('<b>%s</b>' % title)
        hbox.append(icon)
        hbox.append(label)
        return hbox

    def create_scrolledwindow(self):
        scrwin = Gtk.ScrolledWindow()
        scrwin.set_hexpand(True)
        scrwin.set_vexpand(True)
        return scrwin

    def create_view(self, customview, title):
        box = self.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
        label = self.create_label(title)
        view = customview(self.app)
        view.get_style_context().add_class(class_name='monospace')
        view.get_style_context().add_class(class_name='caption')
        view.set_hexpand(True)
        view.set_vexpand(True)
        box.append(label)
        return box, view

    def create_switch_button(self, icon_name, title, callback=None, data=None):
        button = Gtk.Switch()
        if callback is not None:
            button.connect('notify::active', callback, data)
        return button

    def noop(self, *args):
        self.log.debug(args)
