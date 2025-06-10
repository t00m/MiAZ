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

        # Toolbar
        toolbar = factory.create_box_horizontal(margin=0, spacing=0, hexpand=True, vexpand=False)
        toolbar.get_style_context().add_class(class_name='toolbar')
        centerbox = Gtk.CenterBox()
        centerbox.set_hexpand(True)
        toolbar.append(centerbox)
        self.append(toolbar)

        # Left
        self.toolbar_buttons_Av = factory.create_box_horizontal(margin=0, spacing=0, vexpand=False, hexpand=True)
        self.toolbar_buttons_Av.get_style_context().add_class(class_name='linked')
        if self.edit:
            self.toolbar_buttons_Av.set_hexpand(False)
            self.btnAvAdd = factory.create_button(icon_name='io.github.t00m.MiAZ-list-add-symbolic', title='', callback=self._on_item_available_add)
            self.toolbar_buttons_Av.append(self.btnAvAdd)
            self.btnAvRemove = factory.create_button(icon_name='io.github.t00m.MiAZ-list-remove-symbolic', title='', callback=self._on_item_available_remove)
            self.toolbar_buttons_Av.append(self.btnAvRemove)
            self.btnAvEdit = factory.create_button(icon_name='io.github.t00m.MiAZ-list-edit-symbolic', title='', callback=self._on_item_available_edit)
            self.toolbar_buttons_Av.append(self.btnAvEdit)
        centerbox.set_start_widget(self.toolbar_buttons_Av)

        # Center
        self.toolbar_buttons_center = factory.create_box_horizontal(margin=0, spacing=0, vexpand=False, hexpand=False)
        self.toolbar_buttons_center.get_style_context().add_class(class_name='linked')
        centerbox.set_center_widget(self.toolbar_buttons_center)

        ## Add to used
        self.btnAddToUsed = factory.create_button('io.github.t00m.MiAZ-selector-add', callback=self._on_item_used_add, reverse=True)
        self.toolbar_buttons_center.append(self.btnAddToUsed)

        ## Search entry
        self.searchentry = Gtk.SearchEntry()
        self.searchentry.set_placeholder_text(_('Type here for filtering entries'))
        self.searchentry.connect('search-changed', self._on_filter_selected)
        self.searchentry.connect('search-started', self._on_filter_selected)
        self.searchentry.connect('activate', self._on_item_available_add, self.config_for)
        self.toolbar_buttons_center.append(self.searchentry)

        # Remove from used
        self.btnRemoveFromUsed = factory.create_button('io.github.t00m.MiAZ-selector-remove', tooltip='disable', callback=self._on_item_used_remove)
        self.toolbar_buttons_center.append(self.btnRemoveFromUsed)

        # Right
        self.toolbar_buttons_Sl = factory.create_box_horizontal(margin=0, spacing=0, vexpand=False, hexpand=True)
        self.toolbar_buttons_Sl.get_style_context().add_class(class_name='linked')
        self.app.add_widget('settings-repository-toolbar-av', toolbar)
        self.toolbar_buttons_Sl.set_halign(Gtk.Align.END)
        centerbox.set_end_widget(self.toolbar_buttons_Sl)

        # Views
        boxViews = factory.create_box_horizontal(margin=0, spacing=0, hexpand=True, vexpand=True)
        boxViews.get_style_context().add_class(class_name='toolbar')
        boxViews.set_homogeneous(True)
        boxLeft = factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        boxRight = factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        boxViews.append(boxLeft)
        boxViews.append(boxRight)
        self.append(boxViews)

        ## Available view
        boxViewAv = factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        self.frmViewAv = Gtk.Frame()
        boxViewAv.append(self.frmViewAv)
        boxLeft.append(boxViewAv)

        ## Used view
        boxViewSl = factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        self.frmViewSl = Gtk.Frame()
        boxViewSl.append(self.frmViewSl)
        boxRight.append(boxViewSl)

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
        i_title = _(item_type.__title__)
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
            window = self.viewSl.get_root()
            title = self.dialog_title
            body1 = _('<b>Action not possible</b>')
            body2 = _('{title} {desc} is still being used by {num_docs} documents').format(title=i_title, desc=item_dsc, num_docs=len(docs))
            body = body1 + '\n' + body2
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
            srvdlg.show_error(title=title, body=body, widget=widget, width=600, height=480, parent=window)
        else:
            self.config.add_available(selected_item.id, selected_item.title)
            self.config.remove_used(selected_item.id)
            self.update_views()
            title = self.dialog_title
            body = _('{title} {desc} disabled').format(title=i_title, desc=item_dsc)
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
                title = self.dialog_title
                body1 = _('<b>Action not possible</b>')
                body2 = _('{title} {value} added to list of available {item_types}').format(title=i_title, value=value, item_types=item_type.__title_plural__.lower())
                body = body1 + '\n' + body2
                self.srvdlg.show_info(title=title, body=body, parent=dialog)
            else:
                title = self.dialog_title
                body1 = _('<b>Action not possible</b>')
                body2 = _('Either the {title} key or the description are empty. Please, check.').format(title=i_title.lower())
                body = body1 + '\n' + body2
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
        title = self.dialog_title
        if not is_used:
            body1 = _('<b>Action not possible</b>')
            body2 = _('Your about to delete <i>{title} {desc}</i>.\n\nAre you sure?').format(title=i_title.lower(), desc=item_dsc)
            body = body1 + '\n' + body2
            dialog = self.srvdlg.show_question(title=title, body=body)
            dialog.connect('response', self._on_item_available_remove_response, selected_item)
            dialog.present(self)
        else:
            value_used, docs = util.field_used(repository.docs, self.config.model, selected_item.id)
            item_type = self.config.model
            i_title = item_type.__title__
            window = self.viewAv.get_root()
            item_desc = selected_item.title.replace('_', ' ')

            if len(docs) > 0:
                body1 = _('<b>Action not possible</b>')
                body2 = _('{title} {desc} is still being used by {num_docs} documents').format(title=i_title, desc=item_desc, num_docs=len(docs))
                body = body1 + '\n' + body2
                items = []
                for doc in docs:
                    items.append(File(id=doc, title=os.path.basename(doc)))
                view = MiAZColumnViewDocuments(self.app)
                view.update(items)
            else:
                body1 = _('<b>Action not possible</b>')
                body2 = _('{title} {desc} is not used by any document.\nHowever, it is enabled.\n\n\nPlease, disable it first before deleting it.').format(title=i_title, desc=item_desc)
                body = body1 + '\n' + body2
                view = None

            if view is not None:
                widget = Gtk.Frame()
                widget.set_child(view)
            else:
                widget = view
            srvdlg = self.app.get_service('dialogs')
            srvdlg.show_error(title=title, body=body, widget=widget, width=600, height=480, parent=window)

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
        title = self.dialog_title
        if response == 'apply':
            self.config.remove_available(selected_item.id)
            self.searchentry.set_text('')
            self.searchentry.activate()
            body = _('{title} {desc} removed from de list of available {item_types}').format(title=i_title, desc=item_dsc, item_types=item_type.__title_plural__.lower())
            self.srvdlg.show_warning(title=title, body=body, parent=self)
        else:
            body = _('{title} {desc} not deleted from de list of available {item_types}').format(title=i_title, desc=item_dsc, item_types=item_type.__title_plural__.lower())
            self.srvdlg.show_info(title=title, body=body, parent=self)

    def _on_item_used_add(self, *args):
        items_used = self.config.load_used()
        selected_item = self.viewAv.get_selected()
        is_used = selected_item.id in items_used
        item_type = self.config.model
        i_title = item_type.__title__
        title = self.dialog_title
        if not is_used:
            items_used[selected_item.id] = selected_item.title
            self.config.save_used(items=items_used)
            self.update_views()
            body = _('{title} {item} has been enabled').format(title=i_title, item=selected_item.title)
            self.srvdlg.show_info(title=title, body=body, parent=self)
        else:
            body1 = _('<b>Action not possible</b>')
            body2 = _('{title} {item} is already enabled').format(title=i_title, item=selected_item.title)
            body = body1 + '\n' + body2
            self.srvdlg.show_error(title=title, body=body, parent=self)
