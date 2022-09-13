#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gi
from gi.repository import Gio

def get_file_mimetype(path):
    mimetype, val = Gio.content_type_guess('filename=%s' % path, data=None)
    return mimetype

