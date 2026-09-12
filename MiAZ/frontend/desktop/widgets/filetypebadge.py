# File: filetypebadge.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: What stands in for a page when a document has no preview

import os
from gettext import gettext as _

from gi.repository import Gio
from gi.repository import Gtk


class MiAZFileTypeBadge(Gtk.Box):
    """The icon of the file type and its extension, in place of a page.

    Only PDFs and images render a preview. A Word file or a spreadsheet
    would otherwise leave a hole where the page goes, and the hole does not
    say why. The icon comes from the content type GIO guesses from the name,
    so the theme's office, spreadsheet and text icons are used when it has
    them and a generic file icon otherwise.
    """
    __gtype_name__ = 'MiAZFileTypeBadge'

    def __init__(self, pixel_size=48):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.add_css_class('miaz-filetype-badge')
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)
        self.icon = Gtk.Image()
        self.icon.set_pixel_size(pixel_size)
        self.label = Gtk.Label()
        self.label.add_css_class('caption-heading')
        self.label.add_css_class('dim-label')
        self.append(self.icon)
        self.append(self.label)

    def set_filepath(self, filepath):
        ext = os.path.splitext(filepath)[1].lower()
        self.label.set_text(ext[1:].upper() if ext else _('File'))
        content_type, _uncertain = Gio.content_type_guess(os.path.basename(filepath), None)
        self.icon.set_from_gicon(Gio.content_type_get_icon(content_type))
        self.set_tooltip_text(_('No preview'))
