#!/usr/bin/python3
# File: widget.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Not used

from MiAZ.backend.log import MiAZLog

class MiAZWidget(object):
    """Widget helper class for MiAZ widgets"""
    log = None

    def __init__(self, app, name=None):
        """Initialize Service instance"""
        # ~ GObject.GObject.__init__(self)
        self.app = app
        if name is None:
            name = __class__.__name__
        self.name = name
        self.log = MiAZLog(name)
