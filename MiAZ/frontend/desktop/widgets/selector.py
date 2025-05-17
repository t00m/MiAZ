#!/usr/bin/python3
# File: selector.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Custom widget to manage available/used config items

import os
import sys
from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewDocuments
from MiAZ.frontend.desktop.services.dialogs import MiAZDialogAdd
from MiAZ.backend.models import Country, Plugin, File


class MiAZSelector(Gtk.Box):
    def __init__(self, app, edit=True):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True, spacing=0)
        self.log = MiAZLog('MiAZ.Selector')
        self.app = app
        self.edit = edit
        self.config = None
        self.viewAv = None
        self.viewSl = None
        self._build_ui()

    def _build_ui(self):
        factory = self.app.get_service('factory')
        ENV = self.app.get_env()

        # Banner
        title = "One or more plugins were disabled. Application restart needed."
        banner = self.app.add_widget('repository-settings-banner', Adw.Banner.new(title))
        banner.set_button_label('restart')
        banner.connect('button-clicked', self._on_restart_clicked)
        restart_needed = ENV['APP']['STATUS']['RESTART_NEEDED']
        banner.set_revealed(restart_needed)
        self.append(banner)

        # Views
        boxViews = factory.create_box_horizontal(spacing=0, hexpand=True, vexpand=True)
        boxViews.set_homogeneous(True)
        boxLeft = factory.create_box_vertical(spacing=0, hexpand=True, vexpand=True)
        boxRight = factory.create_box_vertical(spacing=0, hexpand=True, vexpand=True)
        boxViews.append(boxLeft)
        boxViews.append(boxRight)
        self.append(boxViews)

        ## Available view
        boxViewAv = factory.create_box_vertical(hexpand=True, vexpand=True)
        boxViewAv.get_style_context().add_class(class_name='toolbar')
        self.frmViewAv = Gtk.Frame()
        boxViewAv.append(self.frmViewAv)
        toolbar = Gtk.CenterBox()
        self.app.add_widget('settings-repository-toolbar-av', toolbar)
        toolbar.get_style_context().add_class(class_name='toolbar')
        self.toolbar_buttons_Av = factory.create_box_horizontal(margin=0, spacing=0, vexpand=False, hexpand=True)
        if self.edit:
            self.toolbar_buttons_Av.set_hexpand(False)
            self.btnAvAdd = factory.create_button(icon_name='io.github.t00m.MiAZ-list-add-symbolic', title='', callback=self._on_item_available_add, css_classes=['flat'])
            self.toolbar_buttons_Av.append(self.btnAvAdd)
            self.btnAvRemove = factory.create_button(icon_name='io.github.t00m.MiAZ-list-remove-symbolic', title='', callback=self._on_item_available_remove, css_classes=['flat'])
            self.toolbar_buttons_Av.append(self.btnAvRemove)
            self.btnAvEdit = factory.create_button(icon_name='io.github.t00m.MiAZ-list-edit-symbolic', title='', callback=self._on_item_available_edit, css_classes=['flat'])
            self.toolbar_buttons_Av.append(self.btnAvEdit)
        self.btnAddToUsed = factory.create_button('io.github.t00m.MiAZ-selector-add', callback=self._on_item_used_add, css_classes=['flat', 'success'], reverse=True)
        toolbar.set_start_widget(self.toolbar_buttons_Av)
        toolbar.set_end_widget(self.btnAddToUsed)
        boxLeft.append(toolbar)
        boxLeft.append(boxViewAv)

        ## Used view
        boxViewSl = factory.create_box_vertical(hexpand=True, vexpand=True)
        boxViewSl.get_style_context().add_class(class_name='toolbar')
        self.frmViewSl = Gtk.Frame()
        boxViewSl.append(self.frmViewSl)
        toolbar = Gtk.CenterBox()
        self.app.add_widget('settings-repository-toolbar-sl', toolbar)
        toolbar.get_style_context().add_class(class_name='toolbar')
        self.toolbar_buttons_Sl = factory.create_box_horizontal(margin=0, spacing=0, vexpand=False, hexpand=True)
        self.toolbar_buttons_Sl.set_halign(Gtk.Align.END)
        self.btnRemoveFromUsed = factory.create_button('io.github.t00m.MiAZ-selector-remove', tooltip='disable', callback=self._on_item_used_remove, css_classes=['flat', 'error'])
        toolbar.set_start_widget(self.btnRemoveFromUsed)
        toolbar.set_end_widget(self.toolbar_buttons_Sl)
        boxRight.append(toolbar)
        boxRight.append(boxViewSl)

        # Search entry
        self.searchentry = Gtk.SearchEntry()
        self.searchentry.set_placeholder_text('Type here for filtering entries')
        self.searchentry.connect('search-changed', self._on_filter_selected)
        self.searchentry.connect('search-started', self._on_filter_selected)
        self.searchentry.connect('activate', self._on_item_available_add, self.config_for)
        self.toolbar_buttons_Av.append(self.searchentry)

    def _on_restart_clicked(self, *args):
        actions = self.app.get_service('actions')
        actions.application_restart()

    def _add_columnview_available(self, columnview):
        columnview.set_filter(self._do_filter_view)
        columnview.column_title.set_expand(True)
        columnview.cv.connect("activate", self._on_selected_item_available_notify)
        self.frmViewAv.set_child(columnview)
        columnview.cv.sort_by_column(columnview.column_id, Gtk.SortType.ASCENDING)
        filter_model = columnview.get_model_filter()
        selection = Gtk.SingleSelection.new(filter_model)
        columnview.cv.set_model(selection)

    def _on_selection_change(self, *args):
        self.log.debug(args)

    def _add_columnview_used(self, columnview):
        columnview.set_filter(self._do_filter_view)
        columnview.column_title.set_expand(True)
        self.frmViewSl.set_child(columnview)
        columnview.cv.sort_by_column(columnview.column_id, Gtk.SortType.ASCENDING)
        filter_model = columnview.get_model_filter()
        selection = Gtk.SingleSelection.new(filter_model)
        columnview.cv.set_model(selection)

    def _setup_view_finish(self, *args):
        self.log.debug(f"Setup selector for {self.config_for}")

    def update_views(self, *args):
        self._update_view_available()
        self._update_view_used()
        self.viewAv.cv.sort_by_column(self.viewAv.column_id, Gtk.SortType.ASCENDING)
        self.viewSl.cv.sort_by_column(self.viewSl.column_id, Gtk.SortType.ASCENDING)

    def _on_item_used_remove(self, *args):
        # This works only for the standard fields.
        # Others like Projects need their own implementation
        repository = self.app.get_service('repo')
        util = self.app.get_service('util')
        selected_item = self.viewSl.get_selected()
        if selected_item is None:
            return

        item_type = self.config.model
        i_title = item_type.__title__
        item_dsc = selected_item.title.replace('_', ' ')
        items_used = self.config.load_used()
        items_available = self.config.load_available()
        try:
            is_used, docs = util.field_used(repository.docs, self.config.model, selected_item.id)
        except KeyError:
            # FIXME
            # Above call works out only for MiAZ standard fields.
            # For plugins, find another solution
            self.log.warning(f"Custom model for {self.config.config_for} returns False")
            is_used = False
        if is_used:
            text = _(f'{i_title} {item_dsc} is still being used by {len(docs)} documents')
            window = self.viewSl.get_root()
            title = "Action not possible"
            if len(docs) > 0:
                items = []
                for doc in docs:
                    items.append(File(id=doc, title=os.path.basename(doc)))
                view = MiAZColumnViewDocuments(self.app)
                view.update(items)
            else:
                view = None

            if view is not None:
                widget = Gtk.Frame()
                widget.set_child(view)
            else:
                widget = view
            srvdlg = self.app.get_service('dialogs')
            srvdlg.show_error(title=title, body=text, widget=widget, width=600, height=480, parent=window)
        else:
            self.config.add_available(selected_item.id, selected_item.title)
            self.config.remove_used(selected_item.id)
            self.update_views()
            title = f"{i_title} management"
            body = f"{i_title} {item_dsc} disabled"
            self.srvdlg.show_warning(title=title, body=body, parent=self)

    def _on_item_available_add(self, *args):
        if self.edit:
            search_term = self.searchentry.get_text()
            item_type = self.config.model
            i_title = item_type.__title__
            this_item = MiAZDialogAdd(self.app)
            parent = self.get_root()
            title = _(f'Add new {i_title.lower()}')
            key1 = _(f'<b>{i_title.title()} key</b>')
            key2 = _('<b>Description</b>')
            dialog = this_item.create(parent=parent, title=title, key1=key1, key2=key2)
            dialog.connect('response', self._on_item_available_add_response, this_item)
            this_item.set_value1(search_term)
            dialog.present(parent)

    def _on_item_available_add_response(self, dialog, response, this_item):
        item_type = self.config.model
        i_title = item_type.__title__

        if response ==  'apply':
            key = this_item.get_value1()
            value = this_item.get_value2()
            if len(key) > 0 and len(value) > 0:
                self.config.add_available(key.upper(), value)
                self.update_views()
                title = f"{i_title} management"
                body = f"{i_title} {value} added to list of available {item_type.__title_plural__.lower()}"
                self.srvdlg.show_info(title=title, body=body, parent=dialog)
            else:
                title = "Action not possible"
                body = f"Either the {i_title.lower()} key or the description are empty. Please, check."
                self.srvdlg.show_error(title=title, body=body, parent=dialog)

    def _on_item_available_edit(self, *args):
        try:
            item = self.viewAv.get_selected()
            item_type = self.config.model
            i_title = item_type.__title__
            if item_type not in [Country, Plugin]:
                parent = self.get_root()
                title = _(f'Change {i_title.lower()} description')
                key1 = _(f'<b>{i_title.title()} key</b>')
                key2 = _('<b>Description</b>')
                this_item = MiAZDialogAdd(self.app)
                dialog = this_item.create(parent=parent, title=title, key1=key1, key2=key2)
                entry1 = this_item.get_entry_key1()
                entry1.set_sensitive(False)
                if item is not None:
                    this_item.set_value1(item.id)
                    this_item.set_value2(item.title)
                dialog.connect('response', self._on_item_available_edit_description, item, this_item)
                dialog.present(parent)
        except IndexError:
            self.log.debug("No item selected. Cancel operation")

    def _on_item_available_edit_description(self, dialog, response, item, this_item):
        item_type = self.config.model
        i_title = item_type.__title__

        if response == 'apply':
            oldkey = item.id
            oldval = item.title
            newkey = this_item.get_value1()
            newval = this_item.get_value2()
            self.log.debug(f"{oldval} == {newval}? {newval != oldval}")
            if newval != oldval:
                items_used = self.config.load_used()
                if oldkey in items_used:
                    items_used[oldkey] = newval
                    self.config.save_used(items_used)
                items_available = self.config.load_available()
                items_available[oldkey] = newval
                self.config.save_available(items_available)
                self.update_views()
                title = f"{i_title} management"
                body = f"{i_title} <i>{oldval}</i> renamed to <i>{newval}</i> globally"
                self.srvdlg.show_info(title=title, body=body, parent=dialog)
            else:
                title = "Rename not possible"
                body = f"Both {i_title.lower()} descriptions are the same"
                self.srvdlg.show_error(title=title, body=body, parent=dialog)

    def select_item(self, view, item_id):
        self.log.debug(f"{view} > {item_id}")
        model = view.get_model_filter()
        selection = view.get_selection()
        n = 0
        for item in model:
            if item.id == item_id:
                self.log.debug(item)
                selection.unselect_all()
                selection.set_selected(n)
                self._on_item_used_remove()
                break
            n += 1

    def _on_item_available_remove(self, *args):
        repository = self.app.get_service('repo')
        util = self.app.get_service('util')
        selected_item = self.viewAv.get_selected()
        if selected_item is None:
            return

        items_available = self.config.load_available()
        item_type = self.config.model
        i_title = item_type.__title__
        item_id = selected_item.id.replace('_', ' ')
        item_dsc = selected_item.title

        items_used = self.config.load_used()
        is_used = selected_item.id in items_used
        self.log.debug(f"Is '{selected_item.id}' used? {is_used}")
        if not is_used:
            title = f"{i_title} management"
            body = f"Your about to delete <i>{i_title.lower()} {item_dsc}</i>.\n\nAre you sure?"
            dialog = self.srvdlg.show_question(title=title, body=body)
            dialog.connect('response', self._on_item_available_remove_response, selected_item)
            dialog.present(self)
        else:
            value_used, docs = util.field_used(repository.docs, self.config.model, selected_item.id)
            item_type = self.config.model
            i_title = item_type.__title__
            window = self.viewAv.get_root()
            title = "Action not possible"
            item_desc = selected_item.title.replace('_', ' ')

            if len(docs) > 0:
                text = _(f'{i_title} {item_desc} is still being used by {len(docs)} docs')
                items = []
                for doc in docs:
                    items.append(File(id=doc, title=os.path.basename(doc)))
                view = MiAZColumnViewDocuments(self.app)
                view.update(items)
            else:
                text = _(f"{i_title} {item_desc} is not used by any document.\nHowever, it is enabled.\n\n\nPlease, disable it first before deleting it.")
                view = None

            if view is not None:
                widget = Gtk.Frame()
                widget.set_child(view)
            else:
                widget = view
            srvdlg = self.app.get_service('dialogs')
            srvdlg.show_error(title=title, body=text, widget=widget, width=600, height=480, parent=window)

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
        self.log.debug(f"Update available view {self.config.config_for} with {len(items)} items")

    def _update_view_used(self):
        items_used = []
        item_type = self.config.model
        items = self.config.load_used()
        for key in items:
            items_used.append(item_type(id=key, title=items[key]))
        self.viewSl.update(items_used)
        self.log.debug(f"Update used view {self.config.config_for} with {len(items)} items")

    def _on_filter_selected(self, *args):
        self.viewAv.refilter()
        self.viewSl.refilter()

    def _do_filter_view(self, item, filter_list_model):
        chunk = self.searchentry.get_text().upper()
        string = f"{item.id}-{item.title}"
        if chunk in string.upper():
            return True
        return False

    def _on_config_import(self, *args):
        pass

    def _on_item_available_remove_response(self, dialog, response, selected_item):
        item_type = self.config.model
        i_title = item_type.__title__
        item_id = selected_item.id.replace('_', ' ')
        item_dsc = selected_item.title
        if response == 'apply':
            self.config.remove_available(selected_item.id)
            self.searchentry.set_text('')
            self.searchentry.activate()
            title = f"{i_title} management"
            body = f"{i_title} {item_dsc} removed from de list of available {item_type.__title_plural__.lower()}"
            self.srvdlg.show_warning(title=title, body=body, parent=self)
        else:
            title = f"{i_title} management"
            body = f"{i_title} {item_dsc} not deleted from the list of available {item_type.__title_plural__.lower()}"
            self.srvdlg.show_info(title=title, body=body, parent=self)

    def _on_item_used_add(self, *args):
        items_used = self.config.load_used()
        selected_item = self.viewAv.get_selected()
        is_used = selected_item.id in items_used
        item_type = self.config.model
        i_title = item_type.__title__
        if not is_used:
            items_used[selected_item.id] = selected_item.title
            self.config.save_used(items=items_used)
            self.update_views()
            self.srvdlg.show_info(title=f"{i_title} management", body=f"{i_title} {selected_item.title} has been enabled", parent=self)
        else:
            self.srvdlg.show_error('Action not possible', f"{i_title} {selected_item.title} is already enabled", parent=self)
