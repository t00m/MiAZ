# File: chip.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Small removable token with a colored pill look

from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango


class MiAZChip(Gtk.Button):
    """Label plus optional close icon; clicking a closable chip emits 'closed'."""
    __gtype_name__ = 'MiAZChip'
    __gsignals__ = {
        'closed': (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    _css_installed = False

    def __init__(self, text='', markup='', style='', closable=True):
        super().__init__()
        self._install_css()
        self.add_css_class('miaz-chip')
        self.add_css_class('flat')
        if style:
            self.add_css_class(f'miaz-chip-{style}')
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.label = Gtk.Label()
        if markup:
            self.label.set_markup(markup)
        else:
            self.label.set_text(text)
        self.label.set_ellipsize(Pango.EllipsizeMode.END)
        self.label.set_max_width_chars(36)
        box.append(self.label)
        if closable:
            icon = Gtk.Image.new_from_icon_name('window-close-symbolic')
            icon.set_pixel_size(12)
            box.append(icon)
            self.connect('clicked', lambda *_a: self.emit('closed'))
        self.set_child(box)

    @classmethod
    def _install_css(cls):
        if cls._css_installed:
            return
        display = Gdk.Display.get_default()
        if display is None:
            return
        css = (
            ".miaz-chip {"
            " min-height: 0;"
            " padding: 2px 4px 2px 12px;"
            " border-radius: 999px;"
            " color: #2b2b2b; }"
            ".miaz-chip:hover {"
            " background-image: image(alpha(currentColor, 0.10)); }"
        )
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode('utf-8'))
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        cls._css_installed = True
