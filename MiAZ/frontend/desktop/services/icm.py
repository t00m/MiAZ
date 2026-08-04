#!/usr/bin/python3
# File: icm.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Icon manager

from gi.repository import Gtk
from gi.repository import Gio
from gi.repository import GObject

from MiAZ.backend.log import MiAZLog


class MiAZIconManager(GObject.GObject):
    """
    Icon Manager for MiAZ.

    It helps to retrieve (custom) icons
    """

    def __init__(self, app):
        """
        Initialize the IconManager service.

        :param app: pointer to MiAZApp
        :type app: MiAZApp
        """
        super().__init__()
        self.app = app
        self.log = MiAZLog('MiAZ.IconManager')
        self._mimetype_icon_cache = {}

    def get_image_by_name(self, name: str, size: int = 24) -> Gtk.Image:
        """
        Get (custom) icon from theme.

        :param name: icon name
        :type name: str
        :param size: icon size
        :type size: int
        :return: an image
        :rtype: Gtk.Image
        """
        image = Gtk.Image.new_from_icon_name(name)
        image.set_pixel_size(size)
        return image

    def get_mimetype_icon_for_extension(self, extension: str):
        """Return the themed icon for a file extension, without touching disk.

        Resolved from the extension alone (Gio.content_type_guess needs no
        real file) and cached, since a repository only ever has a handful of
        distinct extensions. Used by the workspace Type column, whose cell is
        rebound every time a row scrolls back into view: a per-row disk stat
        there would repeat on every scroll.
        """
        extension = extension.lower()
        try:
            return self._mimetype_icon_cache[extension]
        except KeyError:
            content_type, _uncertain = Gio.content_type_guess(f'file.{extension}', None)
            gicon = Gio.content_type_get_icon(content_type)
            self._mimetype_icon_cache[extension] = gicon
            return gicon
