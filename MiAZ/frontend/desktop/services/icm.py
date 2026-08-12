# File: icm.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Icon manager

import os
import shutil

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

    def register_file_icon(self, name: str, filepath: str, target_dir: str = None) -> str:
        """Make an icon file resolvable by name through the icon theme.

        Widgets that take an icon name (a view switcher page, for one) cannot
        take a path, and the icon theme resolves names, not paths. An icon
        shipped as a file, the way plugins ship theirs, is therefore copied
        into the user icon directory, which is on the theme search path, under
        the given unique name.

        :param name: unique icon name callers will use afterwards
        :type name: str
        :param filepath: icon file to export
        :type filepath: str
        :param target_dir: where to export; defaults to ENV['LPATH']['ICONS']
        :type target_dir: str
        :return: the icon name, or None when it could not be exported
        :rtype: str
        """
        if not filepath or not os.path.isfile(filepath):
            return None
        if target_dir is None:
            env = self.app.get_env()
            if env is None:
                return None
            target_dir = env['LPATH']['ICONS']
        extension = os.path.splitext(filepath)[1].lower()
        target = os.path.join(target_dir, f"{name}{extension}")
        try:
            os.makedirs(target_dir, exist_ok=True)
            # Copy only when it is missing or the source moved on, so an
            # updated plugin ships an updated icon without a copy per startup.
            if (not os.path.exists(target)
                    or os.path.getmtime(filepath) > os.path.getmtime(target)):
                shutil.copy2(filepath, target)
                self.log.debug(f"Icon '{name}' exported to {target}")
        except OSError as error:
            self.log.warning(f"Could not export icon '{name}' from {filepath}: {error}")
            return None
        return name

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
