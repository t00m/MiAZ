#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
# File: icons.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Icon manager
"""

from gi.repository import Gtk
from gi.repository import Gio
from gi.repository import GObject


class MiAZIconManager(GObject.GObject):
    """
    Icon Manager for MiAZ
    It helps to retrieve (custom) icons
    """
    gicondict = {}

    def __init__(self, app):
        """
        Initializes the IconManager service.

        :param app: pointer to MiAZApp
        :type app: MiAZApp
        """
        super().__init__()

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

    def get_mimetype_icon(self, mimetype: str) -> Gio.Icon:
        """
        Get icon for a given mimetype.

        :param mimetype: file mimetype
        :type mimetype: str
        :return: an icon
        :rtype: Gio.Icon
        """
        try:
            gicon = self.gicondict[mimetype]
        except KeyError:
            gicon = Gio.content_type_get_icon(mimetype)
            self.gicondict[mimetype] = gicon
        return gicon
