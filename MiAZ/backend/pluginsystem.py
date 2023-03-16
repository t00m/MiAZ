#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: pluginsystem.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: a Plugin System based on Peas
"""

import gi
gi.require_version('Peas', '1.0')
gi.require_version('PeasGtk', '1.0')

from gi.repository import GObject, Peas, PeasGtk

engine = Peas.Engine.get_default()


class MyPlugin(GObject.Object, Peas.Activatable):
    __gtype_name__ = 'MyPlugin'

    def __init__(self, engine):
        super(MyPlugin, self).__init__()
        self.engine = engine

    def do_activate(self):
        print('MyPlugin activated')

    def do_deactivate(self):
        print('MyPlugin deactivated')

    def do_update_state(self):
        pass

info = Peas.PluginInfo.new(
    name='MyPlugin',
    description='A simple plugin',
    version='1.0',
    author='Your Name',
    website='http://www.example.com/',
    license='MIT',
    module='myplugin',
    objtype='MyPlugin',
)
engine.add_plugin(info)