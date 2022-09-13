#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gi
from gi.repository import Gio
from gi.repository import Gtk

def get_file_mimetype(path):
    mimetype, val = Gio.content_type_guess('filename=%s' % path, data=None)
    return mimetype

