# File: docpreview.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Read-only preview pane for one document

import os
from gettext import gettext as _

from gi.repository import Adw
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from MiAZ.env import ENV
from MiAZ.backend.log import MiAZLog
from MiAZ.backend.tasks import run_in_background
from MiAZ.backend.thumbnails import thumbnail_for
from MiAZ.frontend.desktop.widgets.pills import MiAZFieldPills

# Preview widths in pixels. Zooming renders the page again at the new width
# instead of stretching the image it already has, and thumbnail_for keys its
# cache by width, so going back to a size already seen costs nothing.
ZOOM_STEPS = (320, 480, 640, 960, 1280, 1920)

# 640, the width the panel always used.
DEFAULT_ZOOM = 2

# How tall the panel asks to be for a given page width, and the floor below
# which it stops shrinking.
SHEET_HEIGHT_RATIO = 0.62
MIN_SHEET_HEIGHT = 260


class MiAZDocPreview(Gtk.Box):
    """Spinner while rendering, then the page image or a no-preview note."""
    __gtype_name__ = 'MiAZDocPreview'
    __gsignals__ = {
        # The user asked to put the preview away. Whoever is showing it owns
        # the sheet or the panel, so it says so rather than closing itself.
        'close-requested': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.app = app
        self.log = MiAZLog('MiAZDocPreview')
        self._doc = None
        self._zoom = DEFAULT_ZOOM
        # Only the latest request may touch the widget; older renders land late.
        self._token = None

        # The concept names the document, so it leads and the date follows it.
        # The filename is what the document is filed as, not what it is.
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        header.set_margin_top(6)
        header.set_margin_start(12)
        header.set_margin_end(12)
        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        titles.set_hexpand(True)
        self.label_title = Gtk.Label(xalign=0)
        self.label_title.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        self.label_title.add_css_class('heading')
        self.label_subtitle = Gtk.Label(xalign=0)
        self.label_subtitle.set_ellipsize(Pango.EllipsizeMode.END)
        self.label_subtitle.add_css_class('caption')
        self.label_subtitle.add_css_class('dim-label')
        titles.append(self.label_title)
        titles.append(self.label_subtitle)
        header.append(titles)
        header.append(self._build_zoom_controls())
        self.append(header)

        self.pills = MiAZFieldPills()
        self.pills.set_halign(Gtk.Align.CENTER)
        self.pills.set_visible(False)
        self.append(self.pills)

        self.stack = Gtk.Stack()
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)
        empty = Adw.StatusPage()
        empty.set_icon_name('io.github.t00m.MiAZ')
        empty.set_title(_('No document selected'))
        self.spinner = Gtk.Spinner()
        self.spinner.set_halign(Gtk.Align.CENTER)
        self.spinner.set_valign(Gtk.Align.CENTER)
        self.picture = Gtk.Picture()
        # Not can-shrink: with it the picture takes whatever width the panel
        # has and scales the page down to fit, so rendering the page at a
        # bigger size changed only its sharpness and zooming looked dead. At
        # its natural size the page really grows and the window scrolls.
        self.picture.set_can_shrink(False)
        self.picture.set_halign(Gtk.Align.CENTER)
        self.picture.set_valign(Gtk.Align.START)
        scrwin = Gtk.ScrolledWindow()
        scrwin.set_child(self.picture)
        none_page = Adw.StatusPage()
        none_page.set_icon_name('io.github.t00m.MiAZ')
        none_page.set_title(_('No preview available'))
        self.stack.add_named(empty, 'empty')
        self.stack.add_named(self.spinner, 'loading')
        self.stack.add_named(scrwin, 'picture')
        self.stack.add_named(none_page, 'none')
        self.append(self.stack)
        self.stack.set_visible_child_name('empty')
        self._apply_zoom()

    def _build_zoom_controls(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        outer.set_valign(Gtk.Align.CENTER)
        # The preview is the first page. Reading the rest of the document, or
        # anything the renderer cannot draw, still means opening it properly.
        self.button_open = Gtk.Button.new_from_icon_name('document-open-symbolic')
        self.button_open.set_tooltip_text(_('Open in the default application'))
        self.button_open.add_css_class('flat')
        self.button_open.connect('clicked', lambda *_a: self.open_document())
        outer.append(self.button_open)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        box.add_css_class('linked')
        box.set_valign(Gtk.Align.CENTER)
        self.button_zoom_out = Gtk.Button.new_from_icon_name('zoom-out-symbolic')
        self.button_zoom_out.set_tooltip_text(_('Show the page smaller'))
        self.button_zoom_out.add_css_class('flat')
        self.button_zoom_out.connect('clicked', lambda *_a: self.zoom_out())
        self.button_zoom_in = Gtk.Button.new_from_icon_name('zoom-in-symbolic')
        self.button_zoom_in.set_tooltip_text(_('Show the page bigger'))
        self.button_zoom_in.add_css_class('flat')
        self.button_zoom_in.connect('clicked', lambda *_a: self.zoom_in())
        box.append(self.button_zoom_out)
        box.append(self.button_zoom_in)
        outer.append(box)
        outer.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        self.button_hide = Gtk.Button.new_from_icon_name('window-close-symbolic')
        self.button_hide.set_tooltip_text(_('Hide the preview'))
        self.button_hide.add_css_class('flat')
        self.button_hide.connect('clicked', lambda *_a: self.emit('close-requested'))
        outer.append(self.button_hide)
        return outer

    def open_document(self):
        """Hand the document to whatever the desktop opens it with."""
        if not self._doc:
            return
        self.app.get_service('actions').document_display(os.path.basename(self._doc))

    def get_document(self):
        return self._doc

    def get_zoom_width(self):
        return ZOOM_STEPS[self._zoom]

    def zoom_in(self):
        self._set_zoom(self._zoom + 1)

    def zoom_out(self):
        self._set_zoom(self._zoom - 1)

    def _set_zoom(self, level):
        level = max(0, min(level, len(ZOOM_STEPS) - 1))
        if level == self._zoom:
            return
        self._zoom = level
        self._apply_zoom()
        # Render the page again at the new width rather than scaling the old
        # image up, so zooming in shows more of the page and not bigger pixels.
        if self._doc:
            self.set_document(self._doc)

    def _apply_zoom(self):
        self.button_zoom_out.set_sensitive(self._zoom > 0)
        self.button_zoom_in.set_sensitive(self._zoom < len(ZOOM_STEPS) - 1)
        # The panel grows with the page, so zooming in is worth doing in a
        # bottom sheet: an Adw.BottomSheet takes the height its sheet asks for.
        # Capped, because the sheet must not swallow the whole window.
        window = self.get_root()
        available = window.get_height() if window is not None else 0
        wanted = int(ZOOM_STEPS[self._zoom] * SHEET_HEIGHT_RATIO)
        if available:
            wanted = min(wanted, int(available * 0.75))
        self.set_size_request(-1, max(MIN_SHEET_HEIGHT, wanted))

    def set_document(self, filepath):
        self._doc = filepath
        token = self._token = object()
        if not filepath:
            self.label_title.set_text('')
            self.label_subtitle.set_text('')
            self.pills.set_visible(False)
            self.set_tooltip_text(None)
            self.spinner.stop()
            self.stack.set_visible_child_name('empty')
            return
        self._set_titles(filepath)
        self.stack.set_visible_child_name('loading')
        self.spinner.start()
        cache_dir = os.path.join(ENV['LPATH']['CACHE'], 'thumbnails')
        width = ZOOM_STEPS[self._zoom]
        run_in_background(lambda: thumbnail_for(filepath, cache_dir, scale=width),
                          on_done=lambda path: self._on_rendered(token, path),
                          on_error=lambda error: self._on_failed(token, error),
                          name='doc-preview')

    def _set_titles(self, filepath):
        basename = os.path.basename(filepath)
        util = self.app.get_service('util')
        fields = util.get_fields(basename)
        self.pills.set_visible(len(fields) == 7)
        if len(fields) == 7:
            # The index knows the descriptions; a document it has not seen
            # (the rename dialog previewing a file from outside) shows keys.
            item = self.app.get_service('index').document(basename)
            if item is not None and item.valid:
                self.pills.set_item(item)
            else:
                self.pills.set_fields(fields)
            self.label_title.set_text(fields[5].replace('_', ' '))
            self.label_subtitle.set_text(
                util.filename_date_human_simple(fields[0]) or _('No date'))
        else:
            # Not filed under the convention, so there is no concept to lead with.
            self.label_title.set_text(basename)
            self.label_subtitle.set_text('')
        self.set_tooltip_text(basename)

    def _on_rendered(self, token, path):
        if token is not self._token:
            return
        self.spinner.stop()
        if path:
            self.picture.set_filename(path)
            self.stack.set_visible_child_name('picture')
        else:
            self.stack.set_visible_child_name('none')

    def _on_failed(self, token, error):
        if token is not self._token:
            return
        self.log.warning(f"Preview failed: {error}")
        self.spinner.stop()
        self.stack.set_visible_child_name('none')
