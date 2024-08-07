#!/usr/bin/python
# File: icm.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Icon manager

import os

from gi.repository import Gtk
from gi.repository import Gio
from gi.repository import GObject

from MiAZ.backend.log import MiAZLog


class MiAZIconManager(GObject.GObject):
    """
    Icon Manager for MiAZ.

    It helps to retrieve (custom) icons
    """

    gicondict = {}

    def __init__(self, app):
        """
        Initialize the IconManager service.

        :param app: pointer to MiAZApp
        :type app: MiAZApp
        """
        super().__init__()
        self.app = app
        self.log = MiAZLog('MiAZ.IconManager')

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

    def get_mimetype_icon(self, filename: str) -> Gio.Icon:
        """
        Get mimetype icon for a given file.

        :param filename: file name
        :type filename: str
        return: an icon
        rtype: Gio.ThemedIcon (GIcon)
        """
        repository = self.app.get_service('repo')
        basedir = repository.docs
        filepath = os.path.join(basedir, filename)
        if os.path.exists(filepath):
            gfile = Gio.File.new_for_path(filepath)
            info = gfile.query_info(Gio.FILE_ATTRIBUTE_STANDARD_ICON, Gio.FileQueryInfoFlags.NONE, None)
            gicon = info.get_icon()
            return gicon