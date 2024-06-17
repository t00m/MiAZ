#!/usr/bin/python3

"""
# File: selector.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Custom widget to manage available/used config items
"""

import os
from gettext import gettext as _

from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewDocuments
from MiAZ.frontend.desktop.widgets.dialogs import MiAZDialogAdd
from MiAZ.frontend.desktop.widgets.dialogs import CustomDialog
from MiAZ.backend.models import Country, Plugin, File


class MiAZSelector(Gtk.Box):
    def __init__(self, app, edit=True):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True, spacing=0)
        self.log = MiAZLog('MiAZ.Selector')
        self.app = app
        self.edit = edit
        self.actions = self.app.get_service('actions')
        self.util = self.app.get_service('util')
        self.factory = self.app.get_service('factory')
        self.repository = self.app.get_service('repository')
        self.config = None
        self.viewAv = None
        self.viewSl = None
        self._setup_ui()

    def _setup_ui(self):
        # Entry and buttons for operations (edit/add/remove)
        self.boxOper = Gtk.Box(spacing=3, orientation=Gtk.Orientation.HORIZONTAL)
        self.boxOper.set_margin_top(24)
        self.boxOper.set_margin_bottom(6)
        self.boxOper.set_margin_start(6)
        self.boxOper.set_margin_end(6)
        self.boxOper.set_hexpand(True)
        self.boxOper.set_vexpand(False)
        boxEntry = Gtk.Box(spacing=0, orientation=Gtk.Orientation.HORIZONTAL)
        boxEntry.set_hexpand(False)
        self.entry = Gtk.Entry()
        self.entry.get_style_context().add_class(class_name='caption')
        self.entry.set_activates_default(True)
        self.entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, 'miaz-entry-clear')
        self.entry.set_icon_activatable(Gtk.EntryIconPosition.SECONDARY, True)
        self.entry.connect('icon-press', self._on_entrysearch_delete)
        self.entry.connect('changed', self._on_filter_selected)
        self.entry.connect('activate', self._on_item_available_add, self.config_for)
        self.entry.set_hexpand(True)
        self.entry.set_has_frame(True)
        self.entry.set_placeholder_text('Type here for filtering')
        boxEntry.append(self.entry)
        self.boxOper.append(boxEntry)
        if self.edit:
            self.boxButtons = Gtk.Box(spacing=0, orientation=Gtk.Orientation.HORIZONTAL)
            self.boxButtons.get_style_context().add_class(class_name='linked')
            self.boxButtons.set_hexpand(True)
            self.boxButtons.append(self.factory.create_button(icon_name='com.github.t00m.MiAZ-list-add-symbolic', title='', callback=self._on_item_available_add))
            self.boxButtons.append(self.factory.create_button(icon_name='com.github.t00m.MiAZ-list-remove-symbolic', title='', callback=self._on_item_available_remove))
            self.boxButtons.append(self.factory.create_button(icon_name='com.github.t00m.MiAZ-list-edit-symbolic', title='', callback=self._on_item_available_edit))
            self.boxOper.append(self.boxButtons)
        # ~ boxEmpty = self.factory.create_box_horizontal(hexpand=True)
        # ~ self.boxOper.append(boxEmpty)

        # ~ menu = self._setup_menu_config_expimp()
        # ~ menubutton = Gtk.MenuButton(child=self.factory.create_button_content(icon_name='com.github.t00m.MiAZ-config-symbolic'))
        # ~ popover = Gtk.PopoverMenu()
        # ~ popover.set_menu_model(menu)
        # ~ menubutton.set_popover(popover=popover)
        # ~ self.boxOper.append(menubutton)

        self.append(self.boxOper)
        boxViews = self.factory.create_box_horizontal(spacing=0, hexpand=True, vexpand=True)
        boxLeft = self.factory.create_box_vertical(spacing=0, hexpand=True, vexpand=True)
        boxControls = Gtk.CenterBox()
        boxControls.set_orientation(Gtk.Orientation.VERTICAL)
        boxRight = self.factory.create_box_vertical(spacing=0, hexpand=True, vexpand=True)
        boxViews.append(boxLeft)
        boxViews.append(boxControls)
        boxViews.append(boxRight)
        self.append(boxViews)

        # Available
        self.frmViewAv = Gtk.Frame()
        title = Gtk.Label()
        title.set_markup(_('<b>Available</b>'))
        boxLeft.append(title)
        boxLeft.append(self.frmViewAv)

        # Controls
        boxSel = self.factory.create_box_vertical()
        btnAddToUsed = self.factory.create_button('miaz-selector-add', callback=self._on_item_used_add)
        btnRemoveFromUsed = self.factory.create_button('miaz-selector-remove', callback=self._on_item_used_remove)
        boxSel.append(btnAddToUsed)
        boxSel.append(btnRemoveFromUsed)
        boxControls.set_center_widget(boxSel)

        # Used
        self.frmViewSl = Gtk.Frame()
        title = Gtk.Label()
        title.set_markup(_('<b>Used</b>'))
        boxRight.append(title)
        boxRight.append(self.frmViewSl)
        # ~ self._setup_view_finish()

    def _add_columnview_available(self, columnview):
        columnview.set_filter(self._do_filter_view)
        columnview.column_title.set_expand(True)
        columnview.cv.connect("activate", self._on_selected_item_available_notify)
        self.frmViewAv.set_child(columnview)
        columnview.cv.sort_by_column(columnview.column_id, Gtk.SortType.ASCENDING)
        columnview.cv.get_style_context().add_class(class_name='caption')
        filter_model = columnview.get_model_filter()
        selection = Gtk.SingleSelection.new(filter_model)
        columnview.cv.set_model(selection)
        # ~ selection.connect("selection-changed", self._on_selection_change)

    def _on_selection_change(self, *args):
        self.log.debug(args)

    def _add_columnview_used(self, columnview):
        columnview.set_filter(None)
        columnview.column_title.set_expand(True)
        self.frmViewSl.set_child(columnview)
        columnview.cv.sort_by_column(columnview.column_id, Gtk.SortType.ASCENDING)
        columnview.cv.get_style_context().add_class(class_name='caption')
        filter_model = columnview.get_model_filter()
        selection = Gtk.SingleSelection.new(filter_model)
        columnview.cv.set_model(selection)

    def _setup_view_finish(self, *args):
        self.log.debug("Setup selector for %s", self.config_for)

    def update_views(self, *args):
        self._update_view_available()
        self._update_view_used()
        # ~ self.log.debug("Setup selector for %s", self.config.config_for)

    def _on_item_used_add(self, *args):
        items_used = self.config.load_used()
        selected_item = self.viewAv.get_selected()
        items_used[selected_item.id] = selected_item.title
        self.log.debug("Using %s (%s)", selected_item.id, selected_item.title)
        self.config.save_used(items=items_used)
        self._update_view_used()

    def _on_item_used_remove(self, *args):
        selected_item = self.viewSl.get_selected()
        if selected_item is None:
            return

        items_used = self.config.load_used()
        items_available = self.config.load_available()
        is_used, docs = self.util.field_used(self.repository.docs, self.config.model, selected_item.id)
        if is_used:
            item_type = self.config.model
            i_title = item_type.__title__
            text = _('%s %s is still being used by %d docs:') % (i_title, selected_item.title, len(docs))
            window = self.app.get_widget('window')
            dtype = 'error'
            title = "%s %s can't be removed" % (i_title, selected_item.title)
            if len(docs) > 0:
                items = []
                for doc in docs:
                    items.append(File(id=doc, title=os.path.basename(doc)))
                view = MiAZColumnViewDocuments(self.app)
                view.update(items)
            else:
                view = None
            dialog = CustomDialog(app=self.app, parent=window, use_header_bar=True, dtype=dtype, title=title, text=text, widget=view)
            dialog.set_modal(True)
            dialog.show()
        else:
            items_available[selected_item.id] = selected_item.title
            del items_used[selected_item.id]
            self.config.save_used(items=items_used)
            self.config.save_available(items=items_available)
            self.update_views()

    def _on_item_available_add(self, *args):
        if self.edit:
            item_type = self.config.model
            i_title = item_type.__title__
            dialog = MiAZDialogAdd(self.app, self.get_root(), _('Add new %s') % i_title.lower(), _('Key'), _('Description'))
            search_term = self.entry.get_text()
            dialog.set_value1(search_term)
            dialog.connect('response', self._on_response_item_available_add)
            dialog.show()

    def _on_response_item_available_add(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            key = dialog.get_value1()
            value = dialog.get_value2()
            if len(key) > 0:
                self.config.add_available(key.upper(), value)
                self.log.debug("%s (%s) added to list of available items", key, value)
                self.update_views()
        dialog.destroy()

    def _on_item_available_edit(self, *args):
        try:
            item = self.viewAv.get_selected()
            self._on_item_available_rename(item)
        except IndexError:
            self.log.debug("No item selected. Cancel operation")

    def _on_item_available_rename(self, item):
        item_type = self.config.model
        if item_type not in [Country, Plugin]:
            i_title = item_type.__title__
            dialog = MiAZDialogAdd(self.app, self.get_root(), _('Change %s description') % i_title.lower(), _('Key'), _('Description'))
            label1 = dialog.get_label_key1()
            label1.set_text(i_title)
            entry1 = dialog.get_entry_key1()
            entry1.set_sensitive(False)
            dialog.set_value1(item.id)
            dialog.set_value2(item.title)
            dialog.connect('response', self._on_response_item_available_rename, item)
            dialog.show()

    def _on_response_item_available_rename(self, dialog, response, item):
        if response == Gtk.ResponseType.ACCEPT:
            oldkey = item.id
            oldval = item.title
            newkey = dialog.get_value1()
            newval = dialog.get_value2()
            if newval != oldval:
                items_used = self.config.load_used()
                if oldkey in items_used:
                    items_used[oldkey] = newval
                    self.log.debug("%s (%s) renamed to %s (%s) in the list of used items", oldkey, oldval, newkey, newval)
                    self.config.save_used(items_used)
                items_available = self.config.load_available()
                items_available[oldkey] = newval
                self.config.save_available(items_available)

            # ~ if len(newkey) > 0:
                # ~ self.log.debug("Renaming %s (%s) by %s (%s)", oldkey, oldval, newkey, newval)
                # ~ # Rename items used
                # ~ items_used = self.config.load_used()
                # ~ if oldkey in items_used:
                    # ~ if self.config.remove_used(oldkey):
                        # ~ if self.config.add_used(newkey, newval):
                            # ~ self.log.debug("Added %s (%s) to used", newkey, newval)
                # ~ # Rename items available
                # ~ items_available = self.config.load_available()
                # ~ self.config.remove_available(oldkey)
                # ~ self.config.add_available(newkey, newval)
                self.log.debug("%s (%s) renamed to %s (%s) in the list of available items", oldkey, oldval, newkey, newval)
                self.update_views()
        dialog.destroy()

    def select_item(self, view, item_id):
        self.log.debug("%s > %s", view, item_id)
        model = view.get_model_filter()
        selection = view.get_selection()
        n = 0
        for item in model:
            if item.id == item_id:
                self.log.debug(item)
                selection.unselect_all()
                selection.set_selected(n)
                selected_items = view.get_selected_items()
                self.log.error("USED ITEMS SELECTED: %s", selected_items)
                self._on_item_used_remove()
                break
            n += 1

    def _on_item_available_remove(self, *args):
        selected_item = self.viewAv.get_selected()
        if selected_item is None:
            return

        items_used = self.config.load_used()
        is_used = selected_item.id in items_used
        self.log.debug("Is '%s' used? %s", selected_item.id, is_used)
        if not is_used:
            self.config.remove_available_batch([selected_item.id])
            self.update_views()
            self.entry.set_text('')
            self.entry.activate()
        else:
            value_used, docs = self.util.field_used(self.repository.docs, self.config.model, selected_item.id)
            item_type = self.config.model
            i_title = item_type.__title__
            dtype = "warning"
            window = self.app.get_widget('window')
            dtype = 'error'
            title = "%s %s can't be removed" % (i_title, selected_item.title)

            if len(docs) > 0:
                text = _('%s %s is still being used by %d docs:') % (i_title, selected_item.title, len(docs))
                items = []
                for doc in docs:
                    items.append(File(id=doc, title=os.path.basename(doc)))
                view = MiAZColumnViewDocuments(self.app)
                view.update(items)
            else:
                text = _('%s %s is still being used') % (i_title, selected_item.title)
                view = None

            dialog = CustomDialog(app=self.app, parent=window, use_header_bar=True, dtype=dtype, title=title, text=text, widget=view)
            if len(docs) == 0:
                dialog.set_default_size(-1, -1)

            dialog.set_modal(True)
            dialog.show()

    def _on_selected_item_available_notify(self, colview, pos):
        model = colview.get_model()
        item = model.get_item(pos)
        self._on_item_available_rename(item)

    def _update_view_available(self):
        items_available = []
        item_type = self.config.model
        items = self.config.load_available()
        for key in items:
            items_available.append(item_type(id=key, title=items[key]))
        self.viewAv.update(items_available)

    def _update_view_used(self):
        items_used = []
        item_type = self.config.model
        items = self.config.load_used()
        for key in items:
            items_used.append(item_type(id=key, title=items[key]))
        self.viewSl.update(items_used)

    def _on_filter_selected(self, *args):
        self.viewAv.refilter()
        self.viewSl.refilter()

    def _do_filter_view(self, item, filter_list_model):
        chunk = self.entry.get_text().upper()
        string = "%s-%s" % (item.id, item.title)
        if chunk in string.upper():
            return True
        return False

    def _on_entrysearch_delete(self, *args):
        self.entry.set_text("")


    def _on_config_import(self, *args):
        pass
