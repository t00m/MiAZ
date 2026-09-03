# File: gridview.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Grid of document pages, the workspace as thumbnails

import os
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango

from MiAZ.env import ENV
from MiAZ.backend.log import MiAZLog
from MiAZ.backend.thumbnails import request_thumbnail
from MiAZ.frontend.desktop.widgets.filetypebadge import MiAZFileTypeBadge

# Thumbnail widths, in order. The page is rendered at the size it is shown at,
# so a bigger icon is more of the page and not a stretched small one.
ICON_SIZES = (128, 192, 256, 384, 512)

# 256px. Small enough that a screen still holds a useful number of documents.
DEFAULT_SIZE = 2

# A page is taller than it is wide, and roughly A4.
ASPECT = 1.414

# Widest screen worth planning columns for. Gtk.GridView keeps a buffer of
# about 32 rows, so cells built is 32 times max-columns whatever the window is
# actually showing: 24 columns meant 769 cells and 769 pages queued to render
# for a screen holding a dozen. The cap is derived from the icon size instead.
WIDEST_SCREEN = 2560


class GridCell(Gtk.Box):
    """One document: its page, with the seven fields around it.

    Above the page, where a letter carries them: the country and the date on
    the left, the group on the right, then what it is for and who sent it.
    Under the page, what it is about. The recipient is in the tooltip: on a
    grid of pages it was a line of small print nobody was reading.
    """

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.set_halign(Gtk.Align.CENTER)
        self.add_css_class('miaz-grid-cell')
        self.frame = Gtk.Frame()
        self.frame.add_css_class('miaz-grid-page')
        self.picture = Gtk.Picture()
        self.picture.set_can_shrink(True)
        self.picture.set_content_fit(Gtk.ContentFit.CONTAIN)
        self.frame.set_child(self.picture)
        # Shown until the page arrives. When there is none, the file type
        # badge takes its place and says which type it is.
        self.icon = Gtk.Image.new_from_icon_name('io.github.t00m.MiAZ')
        self.icon.set_pixel_size(48)
        self.badge = MiAZFileTypeBadge()
        self.badge.set_visible(False)
        self.overlay = Gtk.Overlay()
        self.overlay.set_child(self.frame)
        self.overlay.add_overlay(self.icon)
        self.overlay.add_overlay(self.badge)
        # Above the page: the flag and the date on the left, the group on the
        # right, then the purpose and the sender on a line of their own. The
        # group names the drawer the document belongs in, so it carries the
        # line and is not dimmed.
        self.flag = Gtk.Image()
        self.flag.set_pixel_size(16)
        self.label_date = self._caption(0)
        self.label_group = self._caption(1)
        self.label_group.add_css_class('caption-heading')
        self.label_group.remove_css_class('dim-label')
        self.label_group.set_hexpand(True)
        self.header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.header.append(self.flag)
        self.header.append(self.label_date)
        self.header.append(self.label_group)
        # The purpose and the sender are the line, so they are bold and the
        # words joining them are not. Undimmed, or the bold would be spent
        # making the text as strong as the rest of the cell.
        self.label_sentby = self._caption(0)
        self.label_sentby.remove_css_class('dim-label')

        # Under the page: what it is about, centred.
        self.label_concept = self._caption(0.5)
        self.label_concept.add_css_class('caption-heading')
        self.label_concept.remove_css_class('dim-label')
        self.label_concept.set_hexpand(True)
        self.footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.footer.append(self.label_concept)

        self.append(self.header)
        self.append(self.label_sentby)
        self.append(self.overlay)
        self.append(self.footer)
        self._doc = None
        self._want = None

    @staticmethod
    def _caption(xalign):
        """A one line field label, cut with an ellipsis when it will not fit."""
        label = Gtk.Label(xalign=xalign)
        label.add_css_class('caption')
        label.add_css_class('dim-label')
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_single_line_mode(True)
        return label

    def update(self, item, view, app):
        size = view.get_icon_size()
        util = app.get_service('util')
        repo = app.get_service('repo')
        basename = os.path.basename(item.id)
        fields = util.get_fields(basename)
        if len(fields) == 7:
            # Descriptions, the way every other view reads them. The keys are
            # in the tooltip and, all at once, in the Filenames view.
            self._set(self.label_date,
                      util.filename_date_human_simple(fields[0]) or _('No date'),
                      f'{_("Date")}: {fields[0]}')
            self._set(self.label_group, item.group_dsc, f'{_("Group")}: {fields[2]}')
            self.label_sentby.set_markup(_('<b>{purpose}</b> sent by <b>{sender}</b>').format(
                purpose=GLib.markup_escape_text(item.purpose_dsc or fields[4]),
                sender=GLib.markup_escape_text(item.sentby_dsc or fields[3])))
            self.label_sentby.set_tooltip_text(
                f'{_("Purpose")}: {fields[4]}\n{_("Sent by")}: {fields[3]}\n'
                f'{_("Sent to")}: {fields[6]}')
            self._set(self.label_concept, item.subtitle.replace('_', ' '), fields[5])
            self.flag.set_from_icon_name(item.country)
            self.flag.set_tooltip_text(f'{item.country_dsc} ({item.country})')
            self.flag.set_visible(True)
        else:
            for label in (self.label_date, self.label_group, self.label_sentby):
                self._set(label, '', '')
            self._set(self.label_concept, basename, basename)
            self.flag.set_visible(False)
        self.set_tooltip_text(basename)
        self.set_size(size)

        filepath = os.path.join(repo.docs, basename)
        self._doc = filepath
        self._want = (filepath, size)
        self.picture.set_paintable(None)
        self.icon.set_visible(True)
        self.badge.set_visible(False)
        cache_dir = os.path.join(ENV['LPATH']['CACHE'], 'thumbnails')

        # Two ways a queued render stops being worth doing. The cell may have
        # been recycled onto another document, which the cell itself knows. Or
        # the whole grid may have changed size, which it does not: resizing
        # rebinds by replacing the model, and that throws the old cells away
        # rather than updating them, so their idea of what they want is frozen
        # at the moment they were discarded. The view is asked too.
        def wanted(want=(filepath, size), asked=size):
            return view.get_icon_size() == asked and self._want == want

        request_thumbnail(
            filepath, cache_dir, size,
            on_done=lambda path, doc=filepath: self._on_page(doc, path),
            is_wanted=wanted)

    @staticmethod
    def _set(label, text, tooltip):
        """Fill a field label, keeping the full value one hover away."""
        label.set_text(text or '')
        label.set_tooltip_text(tooltip or None)

    def set_size(self, size):
        self.frame.set_size_request(size, int(size * ASPECT))
        # The rows are as wide as the page and no wider, so the columns of the
        # grid stay in line whatever a document is called.
        self.header.set_size_request(size, -1)
        self.footer.set_size_request(size, -1)
        half = max(6, size // 16)
        full = max(10, size // 8)
        for label in (self.label_date, self.label_group):
            label.set_max_width_chars(half)
        for label in (self.label_concept, self.label_sentby):
            label.set_max_width_chars(full)
            label.set_size_request(size, -1)

    def _on_page(self, doc, path):
        # The cell may have been recycled for another document meanwhile.
        if doc != self._doc:
            return
        if path is None:
            self.badge.set_filepath(doc)
            self.badge.set_visible(True)
            self.icon.set_visible(False)
            return
        self.picture.set_filename(path)
        self.icon.set_visible(False)


class MiAZGridView(Gtk.Box):
    """The filtered documents as a grid of pages. A pure view, like the timeline."""
    __gtype_name__ = 'MiAZGridView'
    _css_installed = False

    def __init__(self, app, model=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.log = MiAZLog('MiAZGridView')
        self._install_css()
        self._size = DEFAULT_SIZE
        self.button_smaller = None
        self.button_bigger = None
        self._showing = False
        self._rebind_id = None
        # Any Gio.ListModel of MiAZItem works, and the workspace model is
        # already in whatever order the document list is sorted by.
        # The document list's own selection, not a copy: selecting in the
        # grid has to be selecting in the workspace, so the header bar
        # buttons, the plugins and the preview all see the same documents.
        self.view = self.app.get_widget('workspace-view')
        self.selection = None if model is not None else self.view.get_selection()
        if model is None:
            model = self.view.filter_model
        self.model = model
        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', self._on_setup)
        factory.connect('bind', self._on_bind)
        self.gridview = Gtk.GridView(factory=factory)
        self.gridview.set_min_columns(1)
        self.gridview.set_max_columns(self._max_columns())
        self.gridview.add_css_class('miaz-grid')
        self.gridview.connect('activate', self._on_activate)
        self.gridview.set_enable_rubberband(True)
        # Right click opens the same menu the document list does, plugin
        # entries included: it is one menu model, built once by the window.
        self._context_popover = Gtk.PopoverMenu()
        self._context_popover.set_parent(self.gridview)
        self._context_popover.set_has_arrow(False)
        gesture = Gtk.GestureClick.new()
        gesture.set_button(3)
        gesture.connect('pressed', self._on_right_click)
        self.gridview.add_controller(gesture)
        scrwin = Gtk.ScrolledWindow()
        scrwin.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrwin.set_hexpand(True)
        scrwin.set_vexpand(True)
        scrwin.set_child(self.gridview)
        self.append(scrwin)
        self.model.connect('items-changed', self._on_items_changed)
        self.connect('map', lambda *_a: self.set_active(True))
        self.connect('unmap', lambda *_a: self.set_active(False))

    def get_size_controls(self):
        """The page size buttons, for the workspace toolbar to place.

        They live on the toolbar with everything else that belongs to a view,
        rather than on a second toolbar of the grid's own.
        """
        linked = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.button_smaller = Gtk.Button.new_from_icon_name('zoom-out-symbolic')
        self.button_smaller.set_tooltip_text(_('Smaller pages'))
        self.button_smaller.add_css_class('flat')
        self.button_smaller.connect('clicked', lambda *_a: self.smaller())
        self.button_bigger = Gtk.Button.new_from_icon_name('zoom-in-symbolic')
        self.button_bigger.set_tooltip_text(_('Bigger pages'))
        self.button_bigger.add_css_class('flat')
        self.button_bigger.connect('clicked', lambda *_a: self.bigger())
        linked.append(self.button_smaller)
        linked.append(self.button_bigger)
        linked.add_css_class('linked')
        self._update_buttons()
        return linked

    def get_icon_size(self):
        return ICON_SIZES[self._size]

    def _max_columns(self):
        return max(3, min(12, WIDEST_SCREEN // self.get_icon_size()))

    def bigger(self):
        self.set_icon_size(self._size + 1)

    def smaller(self):
        self.set_icon_size(self._size - 1)

    def set_icon_size(self, level):
        level = max(0, min(level, len(ICON_SIZES) - 1))
        if level == self._size:
            return
        self._size = level
        self.gridview.set_max_columns(self._max_columns())
        self._update_buttons()
        # Every cell is rebound, so each page is rendered again at the new size
        # rather than being scaled up from the size it happened to have.
        self._schedule_rebind()

    def _update_buttons(self):
        # The buttons are built when the toolbar asks for them, which may be
        # after a size has already been chosen.
        if getattr(self, 'button_smaller', None) is None:
            return
        self.button_smaller.set_sensitive(self._size > 0)
        self.button_bigger.set_sensitive(self._size < len(ICON_SIZES) - 1)

    def set_active(self, active):
        """Say whether this is the page on screen. Inactive means no model."""
        if active == self._showing:
            return
        self._showing = active
        if active:
            self.gridview.set_model(self._selection_model())
        else:
            self._cancel_rebind()
            self.gridview.set_model(None)

    def _cancel_rebind(self):
        if self._rebind_id is not None:
            GLib.source_remove(self._rebind_id)
            self._rebind_id = None

    def _on_items_changed(self, *args):
        if self._showing:
            self._schedule_rebind()

    def _schedule_rebind(self):
        # The model cannot be swapped from inside its own items-changed
        # emission: GTK is halfway through updating the cells it lists.
        if self._rebind_id is None:
            self._rebind_id = GLib.idle_add(self._rebind)

    def _selection_model(self):
        # A plugin handing in its own model gets a plain selection of its own.
        if self.selection is not None:
            return self.selection
        return Gtk.MultiSelection.new(self.model)

    def _rebind(self):
        self._rebind_id = None
        if self._showing:
            # Taking the model off and putting it back rebinds every cell.
            # The selection object itself is shared with the document list and
            # must not be replaced, only detached for a moment.
            self.gridview.set_model(None)
            self.gridview.set_model(self._selection_model())
        return GLib.SOURCE_REMOVE

    def _on_right_click(self, gesture, n_press, x, y):
        menu_model = self.app.get_widget('workspace-menu-selection')
        if menu_model is None:
            return
        self._context_popover.set_menu_model(menu_model)
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = int(x), int(y), 0, 0
        self._context_popover.set_pointing_to(rect)
        self._context_popover.popup()

    def _on_setup(self, factory, list_item):
        list_item.set_child(GridCell())

    def _on_bind(self, factory, list_item):
        list_item.get_child().update(list_item.get_item(), self, self.app)

    def _on_activate(self, gridview, position):
        item = gridview.get_model().get_item(position)
        self.app.get_service('actions').document_display(item.id)

    @classmethod
    def _install_css(cls):
        if cls._css_installed:
            return
        display = Gdk.Display.get_default()
        if display is None:
            return
        css = (
            ".miaz-grid-cell { padding: 6px; }"
            ".miaz-grid-page {"
            " background-color: #ffffff;"
            " border-radius: 4px; }"
        )
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode('utf-8'))
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        cls._css_installed = True
