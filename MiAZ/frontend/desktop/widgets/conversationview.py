# File: conversationview.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: The filtered documents read as exchanges, one per concept

import os
from gettext import gettext as _
from gettext import ngettext

from gi.repository import Adw
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from MiAZ.env import ENV
from MiAZ.backend.log import MiAZLog
from MiAZ.backend.conversation import (
    Message, conversations, exchanges, home_party, is_outgoing, owner_of)
from MiAZ.backend.thumbnails import request_thumbnail
from MiAZ.backend.util import UNKNOWN_DATE
from MiAZ.frontend.desktop.widgets.filetypebadge import MiAZFileTypeBadge

log = MiAZLog('MiAZ.Conversation')

# Width the page inside a bubble is rendered at.
THUMBNAIL_WIDTH = 240


class ConversationRow(GObject.Object):
    """One entry of the conversation list."""
    __gtype_name__ = 'MiAZConversationRow'

    def __init__(self, conversation):
        super().__init__()
        self.conversation = conversation

    @property
    def title(self):
        return self.conversation.title

    @property
    def count(self):
        return len(self.conversation.messages)


class Bubble(Gtk.Box):
    """One document, drawn as a message.

    The sender is the caption, the date sits beside it, the first page is
    the body. Outgoing sits right, incoming left, the way a chat reads.
    """

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.add_css_class('miaz-bubble')
        self.set_size_request(200, -1)
        self.label_who = Gtk.Label(xalign=0)
        self.label_who.add_css_class('caption-heading')
        self.label_who.set_ellipsize(3)
        self.label_who.set_max_width_chars(40)
        self.label_date = Gtk.Label(xalign=0)
        self.label_date.add_css_class('caption')
        self.label_date.add_css_class('dim-label')
        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        head.append(self.label_who)
        head.append(self.label_date)
        self.label_purpose = Gtk.Label(xalign=0)
        self.label_purpose.add_css_class('caption')
        self.label_purpose.set_wrap(True)
        self.thumbnail = Gtk.Picture()
        self.thumbnail.set_can_shrink(True)
        self.thumbnail.set_size_request(THUMBNAIL_WIDTH, 120)
        self.thumbnail.set_halign(Gtk.Align.START)
        self.thumbnail.add_css_class('miaz-bubble-page')
        self.thumbnail.set_visible(False)
        # Shown instead of the page when the file type has no preview.
        self.badge = MiAZFileTypeBadge()
        self.badge.set_halign(Gtk.Align.START)
        self.badge.set_visible(False)
        self.append(head)
        self.append(self.label_purpose)
        self.append(self.thumbnail)
        self.append(self.badge)
        self._doc = None

    def update(self, item, outgoing, app):
        self.label_who.set_text(item.sentby_dsc or item.sentby_id)
        self.label_date.set_text(_('No date') if item.date == UNKNOWN_DATE else item.date_dsc)
        self.label_purpose.set_text(_('{purpose} to {recipient}').format(
            purpose=item.purpose_dsc or item.purpose,
            recipient=item.sentto_dsc or item.sentto_id))
        self.set_tooltip_text(os.path.basename(item.id))
        self.set_halign(Gtk.Align.END if outgoing else Gtk.Align.START)
        for css in ('miaz-bubble-out', 'miaz-bubble-in'):
            self.remove_css_class(css)
        self.add_css_class('miaz-bubble-out' if outgoing else 'miaz-bubble-in')
        self._load_thumbnail(item, app)

    def _load_thumbnail(self, item, app):
        self.thumbnail.set_visible(False)
        self.badge.set_visible(False)
        repo = app.get_service('repo')
        filepath = os.path.join(repo.docs, os.path.basename(item.id))
        self._doc = filepath
        cache_dir = os.path.join(ENV['LPATH']['CACHE'], 'thumbnails')
        request_thumbnail(
            filepath, cache_dir, THUMBNAIL_WIDTH,
            on_done=lambda path, doc=filepath: self._show_thumbnail(doc, path),
            is_wanted=lambda doc=filepath: doc == self._doc and self.get_root() is not None)

    def _show_thumbnail(self, doc, path):
        if doc != self._doc:
            return
        if path is None:
            self.badge.set_filepath(doc)
            self.badge.set_visible(True)
            return
        self.thumbnail.set_filename(path)
        self.thumbnail.set_visible(True)


class MiAZConversationView(Gtk.Box):
    """The filtered documents as conversations: a list of them, one open.

    A conversation is every document sharing a concept, oldest first, each on
    the side of whoever sent it. The list on the left is ordered by latest
    activity, the way a messaging app orders its threads. Only the open
    conversation builds bubbles and renders pages, so the cost is the size of
    one exchange, not of the repository.
    """
    __gtype_name__ = 'MiAZConversationView'
    _css_installed = False

    def __init__(self, app, model=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.log = MiAZLog('MiAZConversationView')
        self._install_css()
        self._showing = False
        self._stale = True
        self._rebuild_id = None
        self._owner = None
        self._open = None
        self._bubbles = []
        self.view = self.app.get_widget('workspace-view')
        self.selection = None if model is not None else self.view.get_selection()
        if model is None:
            model = self.view.filter_model
        self.model = model

        # The list of conversations.
        self.store = Gio.ListStore(item_type=ConversationRow)
        self.list_selection = Gtk.SingleSelection(model=self.store)
        self.list_selection.set_autoselect(True)
        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', self._on_row_setup)
        factory.connect('bind', self._on_row_bind)
        self.listview = Gtk.ListView(model=self.list_selection, factory=factory)
        self.listview.add_css_class('navigation-sidebar')
        self.list_selection.connect('notify::selected', self._on_conversation_selected)
        list_scroll = Gtk.ScrolledWindow()
        list_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        list_scroll.set_child(self.listview)
        list_scroll.set_vexpand(True)
        self.label_summary = Gtk.Label(xalign=0)
        self.label_summary.add_css_class('dim-label')
        self.label_summary.add_css_class('caption')
        self.label_summary.set_hexpand(True)
        # Most concepts are held by one document. This drops them, so the
        # list is the exchanges, which is what this view is for.
        self.check_exchanges = Gtk.CheckButton(label=_('Only exchanges'))
        self.check_exchanges.add_css_class('caption')
        self.check_exchanges.set_active(True)
        self.check_exchanges.connect('toggled', lambda *_a: self._rebuild())
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        top.set_margin_start(12)
        top.set_margin_end(6)
        top.set_margin_top(6)
        top.set_margin_bottom(6)
        top.append(self.label_summary)
        top.append(self.check_exchanges)
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar.append(top)
        sidebar.append(list_scroll)

        # The open conversation.
        self.label_title = Gtk.Label(xalign=0)
        self.label_title.add_css_class('title-3')
        self.label_title.set_ellipsize(3)
        self.label_parties = Gtk.Label(xalign=0)
        self.label_parties.add_css_class('dim-label')
        self.label_parties.set_ellipsize(3)
        self.button_list = Gtk.Button.new_from_icon_name('sidebar-show-symbolic')
        self.button_list.add_css_class('flat')
        self.button_list.set_tooltip_text(_('Conversations'))
        self.button_list.set_valign(Gtk.Align.CENTER)
        self.button_list.set_visible(False)
        self.button_list.connect('clicked', lambda *_a: self.split.set_show_sidebar(True))
        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        titles.append(self.label_title)
        titles.append(self.label_parties)
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        header.add_css_class('miaz-conversation-header')
        header.append(self.button_list)
        header.append(titles)
        self.thread = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.thread.add_css_class('miaz-conversation-thread')
        self.thread.set_vexpand(True)
        self.thread.set_valign(Gtk.Align.START)
        thread_scroll = Gtk.ScrolledWindow()
        thread_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        thread_scroll.set_child(self.thread)
        thread_scroll.set_vexpand(True)
        self._thread_scroll = thread_scroll
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content.append(header)
        content.append(Gtk.Separator())
        content.append(thread_scroll)

        self.split = Adw.OverlaySplitView()
        self.split.set_sidebar(sidebar)
        self.split.set_content(content)
        self.split.set_min_sidebar_width(200)
        self.split.set_max_sidebar_width(300)
        self.split.set_sidebar_width_fraction(0.3)
        self.split.connect('notify::collapsed', self._on_collapsed)
        self.append(self.split)

        # A narrow window shows one pane at a time.
        mainwindow = self.app.get_widget('mainwindow')
        if mainwindow is not None:
            mainwindow.bind_property('narrow', self.split, 'collapsed',
                                     GObject.BindingFlags.SYNC_CREATE)

        # Right click on a bubble opens the same menu the document list does.
        self._context_popover = Gtk.PopoverMenu()
        self._context_popover.set_parent(self)
        self._context_popover.set_has_arrow(False)

        self.model.connect('items-changed', self._on_items_changed)
        self.connect('map', lambda *_a: self.set_active(True))
        self.connect('unmap', lambda *_a: self.set_active(False))

    def set_active(self, active):
        """Say whether this is the page on screen; inactive builds nothing."""
        if active == self._showing:
            return
        self._showing = active
        if active:
            if self._stale:
                self._rebuild()
        else:
            self._cancel_rebuild()

    def _cancel_rebuild(self):
        if self._rebuild_id is not None:
            GLib.source_remove(self._rebuild_id)
            self._rebuild_id = None

    def _on_items_changed(self, *args):
        self._stale = True
        if self._showing and self._rebuild_id is None:
            # Not from inside the model's own emission: wait for the loop.
            self._rebuild_id = GLib.idle_add(self._rebuild)

    def _on_collapsed(self, split, _pspec):
        self.button_list.set_visible(split.get_collapsed())

    def get_owner(self):
        return self._owner

    def get_conversations(self):
        return [self.store.get_item(i).conversation for i in range(self.store.get_n_items())]

    def get_open(self):
        """The conversation whose bubbles are on screen, or None."""
        return self._open

    def _messages(self):
        for position in range(self.model.get_n_items()):
            item = self.model.get_item(position)
            yield Message(date=item.date, sentby=item.sentby_id, sentto=item.sentto_id,
                          concept=item.subtitle or '', payload=item)

    def _rebuild(self):
        """Group the displayed documents again and keep the open one open."""
        self._rebuild_id = None
        self._stale = False
        messages = list(self._messages())
        self._owner = owner_of(messages)
        # The title is the concept as the user wrote it on the newest document.
        titles = {}
        for message in messages:
            titles.setdefault(message.concept.replace('_', ' ').strip().upper(),
                              message.concept.replace('_', ' ').strip())
        groups = conversations(messages, titles=titles)
        if self.check_exchanges.get_active():
            groups = exchanges(groups)
        was_open = self._open.key if self._open is not None else None
        self.store.remove_all()
        reopen = 0
        for index, conversation in enumerate(groups):
            self.store.append(ConversationRow(conversation))
            if conversation.key == was_open:
                reopen = index
        self.label_summary.set_text(ngettext(
            '{count} conversation', '{count} conversations', len(groups)).format(count=len(groups)))
        if groups:
            self.list_selection.set_selected(reopen)
            self._open_conversation(groups[reopen])
        else:
            self._open_conversation(None)
        return GLib.SOURCE_REMOVE

    def _on_row_setup(self, factory, list_item):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        title = Gtk.Label(xalign=0)
        title.set_ellipsize(3)
        title.add_css_class('heading')
        subtitle = Gtk.Label(xalign=0)
        subtitle.set_ellipsize(3)
        subtitle.add_css_class('caption')
        subtitle.add_css_class('dim-label')
        box.append(title)
        box.append(subtitle)
        box.title = title
        box.subtitle = subtitle
        list_item.set_child(box)

    def _on_row_bind(self, factory, list_item):
        row = list_item.get_item()
        box = list_item.get_child()
        box.title.set_text(row.title or _('No concept'))
        conversation = row.conversation
        first, last = conversation.first_date[:4], conversation.last_date[:4]
        span = first if first == last else f'{first}-{last}'
        count = ngettext('{count} document', '{count} documents', row.count).format(count=row.count)
        box.subtitle.set_text(f'{count} · {span}')
        box.set_tooltip_text(', '.join(conversation.parties))

    def _on_conversation_selected(self, selection, _pspec):
        row = selection.get_selected_item()
        self._open_conversation(row.conversation if row is not None else None)
        if self.split.get_collapsed():
            self.split.set_show_sidebar(False)

    def _open_conversation(self, conversation):
        self._open = conversation
        while (child := self.thread.get_first_child()) is not None:
            self.thread.remove(child)
        self._bubbles = []
        if conversation is None:
            self.label_title.set_text('')
            self.label_parties.set_text('')
            return
        self.label_title.set_text(conversation.title or _('No concept'))
        names = []
        for party in conversation.parties:
            names.append(self._party_name(conversation, party))
        self.label_parties.set_text(_('Between {parties}').format(parties=', '.join(names)))
        home = home_party(conversation, self._owner)
        for message in conversation.messages:
            bubble = Bubble()
            # Into the thread first: the render is skipped for a bubble with
            # no root, and an idle worker can look before this loop moves on.
            self.thread.append(bubble)
            self._bubbles.append(bubble)
            self._attach_gestures(bubble, message.payload)
            bubble.update(message.payload, is_outgoing(message, home), self.app)

    def _party_name(self, conversation, party):
        for message in conversation.messages:
            item = message.payload
            if item.sentby_id == party:
                return item.sentby_dsc or party
            if item.sentto_id == party:
                return item.sentto_dsc or party
        return party

    def _attach_gestures(self, bubble, item):
        click = Gtk.GestureClick.new()
        click.set_button(1)
        click.connect('released', self._on_bubble_click, item)
        bubble.add_controller(click)
        right = Gtk.GestureClick.new()
        right.set_button(3)
        right.connect('pressed', self._on_bubble_right_click, bubble, item)
        bubble.add_controller(right)

    def _select(self, item):
        """Select the document in the workspace, so preview and actions follow."""
        if self.selection is None:
            return
        for position in range(self.model.get_n_items()):
            if self.model.get_item(position) is item:
                self.selection.select_item(position, True)
                return

    def _on_bubble_click(self, gesture, n_press, x, y, item):
        self._select(item)
        if n_press == 2:
            self.app.get_service('actions').document_display(item.id)

    def _on_bubble_right_click(self, gesture, n_press, x, y, bubble, item):
        self._select(item)
        menu_model = self.app.get_widget('workspace-menu-selection')
        if menu_model is None:
            return
        ok, bx, by = bubble.translate_coordinates(self, x, y)
        self._context_popover.set_menu_model(menu_model)
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = int(bx), int(by), 0, 0
        self._context_popover.set_pointing_to(rect)
        self._context_popover.popup()

    @classmethod
    def _install_css(cls):
        if cls._css_installed:
            return
        display = Gdk.Display.get_default()
        if display is None:
            return
        css = (
            ".miaz-conversation-header { padding: 8px 12px; }"
            ".miaz-conversation-thread { padding: 12px; }"
            ".miaz-bubble {"
            " padding: 8px 12px;"
            " border-radius: 12px;"
            " color: #1e1e1e; }"
            ".miaz-bubble-in {"
            " background-color: #ededed;"
            " border-bottom-left-radius: 2px; }"
            ".miaz-bubble-out {"
            " background-color: #d9ecff;"
            " border-bottom-right-radius: 2px; }"
            ".miaz-bubble-page {"
            " background-color: #ffffff;"
            " border-radius: 4px; }"
        )
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode('utf-8'))
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        cls._css_installed = True
