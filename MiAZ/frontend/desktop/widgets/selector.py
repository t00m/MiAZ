# File: selector.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Custom widget to manage available/used config items

import os
from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.util import humanize_value
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
        self._cached_filter_text = ''
        self._build_ui()

    def _build_ui(self):
        factory = self.app.get_service('factory')
        ENV = self.app.get_env()

        # Banner
        title = _("One or more plugins were disabled. Application restart needed.")
        banner = self.app.add_widget('repository-settings-banner', Adw.Banner.new(title))
        banner.set_button_label(_('restart'))
        banner.connect('button-clicked', self._on_restart_clicked)
        restart_needed = ENV['APP']['STATUS']['RESTART_NEEDED']
        banner.set_revealed(restart_needed)
        self.append(banner)

        # Toolbar
        toolbar = factory.create_box_horizontal(margin=0, spacing=0, hexpand=True, vexpand=False)
        toolbar.add_css_class('toolbar')
        centerbox = Gtk.CenterBox()
        centerbox.set_hexpand(True)
        toolbar.append(centerbox)
        self.append(toolbar)

        # Left
        self.toolbar_buttons_Av = factory.create_box_horizontal(margin=0, spacing=0, vexpand=False, hexpand=True)
        self.toolbar_buttons_Av.add_css_class('linked')
        if self.edit:
            self.toolbar_buttons_Av.set_hexpand(False)
            self.btnAvAdd = factory.create_button(icon_name='io.github.t00m.MiAZ-list-add-symbolic', title='', tooltip=_('Add'), callback=self._on_item_available_add)
            self.toolbar_buttons_Av.append(self.btnAvAdd)
            self.btnAvRemove = factory.create_button(icon_name='io.github.t00m.MiAZ-list-remove-symbolic', title='', tooltip=_('Remove'), callback=self._on_item_available_remove)
            self.toolbar_buttons_Av.append(self.btnAvRemove)
            self.btnAvEdit = factory.create_button(icon_name='io.github.t00m.MiAZ-list-edit-symbolic', title='', tooltip=_('Edit'), callback=self._on_item_available_edit)
            self.toolbar_buttons_Av.append(self.btnAvEdit)
        centerbox.set_start_widget(self.toolbar_buttons_Av)

        # Center: only the search entry
        self.toolbar_buttons_center = factory.create_box_horizontal(margin=0, spacing=0, vexpand=False, hexpand=False)
        centerbox.set_center_widget(self.toolbar_buttons_center)

        ## Search entry
        self.searchentry = Gtk.SearchEntry()
        self.searchentry.set_placeholder_text(_('Type here for filtering entries'))
        self.searchentry.connect('search-changed', self._on_filter_selected)
        self.searchentry.connect('search-started', self._on_filter_selected)
        self.searchentry.connect('activate', self._on_item_available_add, self.config_for)
        self.toolbar_buttons_center.append(self.searchentry)

        # Right
        self.toolbar_buttons_Sl = factory.create_box_horizontal(margin=0, spacing=0, vexpand=False, hexpand=True)
        self.toolbar_buttons_Sl.add_css_class('linked')
        if self.edit:
            self.btnSlEdit = factory.create_button(icon_name='io.github.t00m.MiAZ-list-edit-symbolic', title='', tooltip=_('Edit'), callback=self._on_item_used_edit)
            self.toolbar_buttons_Sl.append(self.btnSlEdit)
        self.app.add_widget('settings-repository-toolbar-av', toolbar)
        self.toolbar_buttons_Sl.set_halign(Gtk.Align.END)
        centerbox.set_end_widget(self.toolbar_buttons_Sl)

        # Views
        self.boxViews = factory.create_box_horizontal(margin=0, spacing=0, hexpand=True, vexpand=True)
        self.boxViews.add_css_class('toolbar')
        self.boxViews.set_homogeneous(False)
        self.boxLeft = factory.create_box_vertical(margin=0, spacing=6, hexpand=True, vexpand=True)
        self.boxRight = factory.create_box_vertical(margin=0, spacing=6, hexpand=True, vexpand=True)

        ## Center controls: enable ('>') / disable ('<') selected items
        boxControls = factory.create_box_vertical(margin=6, spacing=0, hexpand=False, vexpand=True)
        boxControls.add_css_class('linked')
        boxControls.set_valign(Gtk.Align.CENTER)
        self.btnAddToUsed = factory.create_button('io.github.t00m.MiAZ-selector-add', tooltip=_('Enable'), callback=self._on_item_used_add)
        self.btnRemoveFromUsed = factory.create_button('io.github.t00m.MiAZ-selector-remove', tooltip=_('Disable'), callback=self._on_item_used_remove)
        boxControls.append(self.btnAddToUsed)
        boxControls.append(self.btnRemoveFromUsed)

        self.boxViews.append(self.boxLeft)
        self.boxViews.append(boxControls)
        self.boxViews.append(self.boxRight)
        self.append(self.boxViews)

        ## Available view
        boxViewAv = factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        self.frmViewAv = Gtk.Frame()
        boxViewAv.append(self.frmViewAv)
        self.boxLeft.append(boxViewAv)

        ## Used view
        boxViewSl = factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        self.frmViewSl = Gtk.Frame()
        boxViewSl.append(self.frmViewSl)
        self.boxRight.append(boxViewSl)

    def _show_toast(self, message: str):
        overlay = None
        widget = self.get_parent()
        while widget is not None:
            if isinstance(widget, Adw.ToastOverlay):
                overlay = widget
                break
            widget = widget.get_parent()
        if overlay is None:
            overlay = self.app.get_widget('toast-overlay')
        if overlay is not None:
            overlay.add_toast(Adw.Toast(title=message))

    def _on_restart_clicked(self, *args):
        actions = self.app.get_service('actions')
        actions.application_restart()

    def _add_columnview_available(self, columnview):
        columnview.set_filter(self._do_filter_view)
        columnview.column_title.set_expand(True)
        columnview.cv.connect("activate", self._on_selected_item_available_notify)
        self.frmViewAv.set_child(columnview)
        columnview.cv.sort_by_column(columnview.column_id, Gtk.SortType.ASCENDING)

    def _on_selection_change(self, *args):
        self.log.debug(args)

    def _add_columnview_used(self, columnview):
        columnview.set_filter(self._do_filter_view)
        columnview.column_title.set_expand(True)
        self.frmViewSl.set_child(columnview)
        columnview.cv.sort_by_column(columnview.column_id, Gtk.SortType.ASCENDING)

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
        selected_items = self.viewSl.get_selected_items()
        if len(selected_items) == 0:
            return

        item_type = self.config.model
        i_title = _(item_type.__title__)

        to_disable = []
        blocked = []  # (item, docs) still referenced by documents
        for item in selected_items:
            try:
                is_used, docs = util.field_used(repository.docs, self.config.model, item.id)
            except KeyError:
                # FIXME
                # Above call works out only for MiAZ standard fields.
                # For plugins, find another solution
                self.log.warning(f"Custom model for {self.config.config_for} returns False")
                is_used = False
                docs = []
            if is_used:
                blocked.append((item, docs))
            else:
                to_disable.append(item)

        if len(to_disable) > 0:
            self.config.add_available_batch([(item.id, item.title) for item in to_disable])
            self.config.remove_used_batch([item.id for item in to_disable])
            self._show_toast(_('{num} {title} disabled').format(num=len(to_disable), title=i_title))

        if len(blocked) > 0:
            window = self.viewSl.get_root()
            title = self.dialog_title
            body1 = _('<b>Action not possible</b>')
            lines = [body1]
            items = []
            for item, docs in blocked:
                item_dsc = item.title.replace('_', ' ')
                lines.append(_('{title} {desc} is still being used by {num_docs} documents').format(title=i_title, desc=item_dsc, num_docs=len(docs)))
                for doc in docs:
                    items.append(File(id=doc, title=os.path.basename(doc)))
            body = '\n'.join(lines)
            if len(items) > 0:
                view = MiAZColumnViewDocuments(self.app)
                view.update(items)
                widget = Gtk.Frame()
                widget.set_child(view)
            else:
                widget = None
            srvdlg = self.app.get_service('dialogs')
            srvdlg.show_error(title=title, body=body, widget=widget, width=600, height=480, parent=window)

    def _on_item_available_add(self, *args):
        if self.edit:
            search_term = self.searchentry.get_text()
            item_type = self.config.model
            i_title = _(item_type.__title__)
            this_item = MiAZDialogAdd(self.app)
            parent = self.searchentry.get_root()
            title = _('Add {title}').format(title=i_title.lower())
            key1 = _('{title} key').format(title=i_title.title())
            key2 = _('Description')
            dialog = this_item.create(parent=parent, title=title, key1=key1, key2=key2, action_label=_('Add'))
            dialog.connect('response', self._on_item_available_add_response, this_item, parent)
            this_item.set_value1(search_term)
            dialog.present(parent)

    def _on_item_available_add_response(self, dialog, response, this_item, parent):
        item_type = self.config.model
        i_title = _(item_type.__title__)

        if response ==  'apply':
            key = this_item.get_value1()
            value = this_item.get_value2()
            if len(key) > 0 and len(value) > 0:
                self.config.add_available(key.upper(), value)
                self.update_views()
                self._show_toast(_('{title} {value} added to list of available {item_types}').format(title=i_title, value=value, item_types=item_type.__title_plural__.lower()))
            else:
                title = self.dialog_title
                body1 = _('<b>Action not possible</b>')
                body2 = _('Either the {title} key or the description are empty. Please, check.').format(title=i_title.lower())
                body = body1 + '\n' + body2
                self.srvdlg.show_error(title=title, body=body, parent=parent)

    def _on_item_available_edit(self, *args):
        self._edit_item_description(self.viewAv)

    def _on_item_used_edit(self, *args):
        self._edit_item_description(self.viewSl)

    def _edit_item_description(self, view):
        # Edit the description of the selected item from either the available
        # or the used view. The change is applied globally (both lists) by
        # _on_item_available_edit_description. Plugins/Countries are excluded.
        item = view.get_selected()
        if item is None:
            self.log.debug("No item selected. Cancel operation")
            return

        item_type = self.config.model
        i_title = _(item_type.__title__)
        if item_type not in [Country, Plugin]:
            parent = self.get_root()
            title = _('Edit {title}').format(title=i_title.lower())
            key1 = _('{title} key').format(title=i_title.title())
            key2 = _('Description')
            this_item = MiAZDialogAdd(self.app)
            dialog = this_item.create(parent=parent, title=title, key1=key1, key2=key2, action_label=_('Save'))
            entry1 = this_item.get_entry_key1()
            entry1.set_sensitive(False)
            this_item.set_value1(item.id)
            this_item.set_value2(item.title)
            dialog.connect('response', self._on_item_available_edit_description, item, this_item, parent)
            dialog.present(parent)

    def _on_item_available_edit_description(self, dialog, response, item, this_item, parent):
        item_type = self.config.model
        i_title = _(item_type.__title__)
        title = self.dialog_title

        if response == 'apply':
            oldkey = item.id
            oldval = item.title
            newkey = this_item.get_value1()
            newval = this_item.get_value2()
            self.log.debug(f"{oldval} == {newval}? {newval != oldval}")
            if newval != oldval:
                # Apply the new description to whichever list(s) hold the key.
                # Available and used are disjoint (enabling an item removes it
                # from available), so guard each write to avoid re-adding a
                # stale orphan entry to the other list.
                items_used = self.config.load_used()
                if oldkey in items_used:
                    items_used[oldkey] = newval
                    self.config.save_used(items_used)
                items_available = self.config.load_available()
                if oldkey in items_available:
                    items_available[oldkey] = newval
                    self.config.save_available(items_available)
                self.update_views()
                self._show_toast(_('{title} {old} renamed to {new} globally').format(title=i_title, old=oldval, new=newval))
            else:
                body1 = _('<b>Action not possible</b>')
                body2 = _('Rename not possible. Both {title} descriptions are the same').format(title=i_title.lower())
                body = body1 + '\n' + body2
                self.srvdlg.show_error(title=title, body=body, parent=parent)

    def select_item(self, view, item_id):
        self.log.debug(f"{view} > {item_id}")
        model = view.get_model_filter()
        selection = view.get_selection()
        for n, item in enumerate(model):
            if item.id == item_id:
                self.log.debug(item)
                selection.unselect_all()
                selection.select_item(n, True)
                self._on_item_used_remove()
                break

    def _on_item_available_remove(self, *args):
        repository = self.app.get_service('repo')
        util = self.app.get_service('util')
        selected_item = self.viewAv.get_selected()
        if selected_item is None:
            return

        item_type = self.config.model
        i_title = item_type.__title__
        item_dsc = selected_item.title

        items_used = self.config.load_used()
        is_used = selected_item.id in items_used
        self.log.debug(f"Is '{selected_item.id}' used? {is_used}")
        title = self.dialog_title
        if not is_used:
            heading = _('Delete {title}?').format(title=i_title.lower())
            body = _('<i>{desc}</i> will be permanently removed.').format(desc=item_dsc)
            dialog = self.srvdlg.show_confirmation(title=heading, body=body, confirm_label=_('Delete'))
            dialog.connect('response', self._on_item_available_remove_response, selected_item)
            dialog.present(self)
        else:
            value_used, docs = util.field_used(repository.docs, self.config.model, selected_item.id)
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
                width = 600
                height = 400
                widget = Gtk.Frame()
                widget.set_child(view)
            else:
                width = -1
                height = -1
                widget = view

            srvdlg = self.app.get_service('dialogs')
            srvdlg.show_error(title=title, body=body, widget=widget, height=height, width=width, parent=window)

    def _on_selected_item_available_notify(self, colview, pos):
        model = colview.get_model()
        item = model.get_item(pos)
        self._on_item_available_rename(item)

    def _update_view_available(self):
        items_available = []
        item_type = self.config.model
        items = self.config.load_available()
        used = self.config.load_used()
        for key in items:
            if key not in used:
                items_available.append(item_type(id=key, title=humanize_value(item_type.__gtype_name__, items[key])))
        self.viewAv.update(items_available)
        self.log.debug(f"Update available view {self.config.config_for} with {len(items_available)} items (filtered {len(items) - len(items_available)} used)")

    def _update_view_used(self, items=None):
        items_used = []
        item_type = self.config.model
        items = self.config.load_used()
        for key in items:
            items_used.append(item_type(id=key, title=humanize_value(item_type.__gtype_name__, items[key])))
        self.viewSl.update(items_used)
        self.log.debug(f"Update used view {self.config.config_for} with {len(items)} items")

    def _on_filter_selected(self, *args):
        self._cached_filter_text = self.searchentry.get_text().upper()
        self.viewAv.refilter()
        self.viewSl.refilter()

    def _do_filter_view(self, item, filter_list_model):
        if not self._cached_filter_text:
            return True
        return self._cached_filter_text in f"{item.id}-{item.title}".upper()

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
            self._show_toast(_('{title} {desc} removed from the list of available {item_types}').format(title=i_title, desc=item_dsc, item_types=item_type.__title_plural__.lower()))
        else:
            self._show_toast(_('{title} {desc} not deleted').format(title=i_title, desc=item_dsc))

    def _on_item_used_add(self, *args):
        selected_items = self.viewAv.get_selected_items()
        if len(selected_items) == 0:
            return

        item_type = self.config.model
        i_title = item_type.__title__
        items_used = self.config.load_used()
        to_enable = [(item.id, item.title) for item in selected_items if item.id not in items_used]
        if len(to_enable) > 0:
            self.config.add_used_batch(to_enable)
            # Only prune the available pool when it is private to this config.
            # SentBy and SentTo share people-available.json (their
            # __config_name_available__ is 'people'), so removing an enabled
            # sender from that pool would also drop it from the recipients'
            # available list, and vice versa. The available view already hides
            # items present in this config's own used list, so keeping the
            # shared pool intact is both correct and sufficient.
            shared_pool = (item_type.__config_name_available__ !=
                           item_type.__config_name_used__)
            if not shared_pool:
                self.config.remove_available_batch([key for key, value in to_enable])
            self._show_toast(_('{num} {title} enabled').format(num=len(to_enable), title=i_title))
