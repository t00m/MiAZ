#!/usr/bin/python3

"""
# File: timelinejs.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Example of MiAZuser plugin
"""

import os
import shutil
from gettext import gettext as _

from gi.repository import GObject

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

plugin_info = {
        'Module':        'timelinejs',
        'Name':          'MiAZTimelineJS',
        'Loader':        'Python3',
        'Description':   _('Create timeline'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2025 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'http://github.com/t00m/MiAZ/README.adoc',
        'Version':       '0.5',
        'Category':      'Visualisation and diagrams',
        'Subcategory':   'Data visualisation'
    }



class MiAZTimelineJSPlugin(MiAZExtension):
    __gtype_name__ = 'MiAZTimelineJSPlugin'
    plugin = None

    def do_activate(self):
        """Plugin activation"""
        # Setup plugin
        ## Get pointer to app
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)

        ## Initialize plugin
        self.plugin.register(self, plugin_info)

        ## Get logger
        self.log = self.plugin.get_logger()

        # Others
        self.actions = self.app.get_service('actions')
        self.util = self.app.get_service('util')
        self.srvdlg = self.app.get_service('dialogs')
        self.factory = self.app.get_service('factory')
        self.webserver = self.app.get_service('webserver')
        self.workspace = self.app.get_widget('workspace')
        self.workspace.connect('workspace-loaded', self.startup)

    def do_deactivate(self):
        self.log.warning("Deactivation not implemented")
        self.plugin.set_started(False)

    def startup(self, *args):
        if not self.plugin.started():
            # Create menu item for plugin
            mnuItemName = self.plugin.get_menu_item_name()
            menuitem = self.factory.create_menuitem(name=mnuItemName, label=_('Display timeline'), callback=self.export)

            # Add plugin to its default (sub)category
            self.plugin.install_menu_entry(menuitem)

            # Plugin configured
            self.plugin.set_started(started=True)

    def export(self, *args):
        ENV = self.app.get_env()
        window = self.workspace.get_root()
        items = self.workspace.get_selected_items()
        if self.actions.stop_if_no_items():
            self.log.debug("No items selected")
            return

        # Generate timeline data
        timelinejs_data = {}
        timelinejs_data['events'] = []
        items_error = []
        for item in items:
            try:
                category = item.group_dsc
                title = item.title
                timestamp = item.date
                url = item.title
                human_date = self.util.filename_date_human(timestamp)
                dt = self.util.string_to_datetime(timestamp)
                event = {}
                text = f"<p>Saved in Category <b>{category}</b> on {human_date}</p><p>Access to <a href='{url}' target='_top'>document</a></p>"
                event['start_date'] = {}
                event['start_date']['year'] = str(dt.year)
                event['start_date']['month'] = str(dt.month)
                event['start_date']['day'] = str(dt.day)
                event['text'] = {}
                event['text']['headline'] = f"{item.purpose_dsc} ({item.subtitle}) sent by {item.sentby_dsc} to {item.sentto_dsc}"
                event['text']['text'] = text
                event['group'] = category
                timelinejs_data['events'].append(event)
            except AttributeError as error:
                items_error.append(item)
        if len(items_error) > 0:
            body = _("At least {count} documents couldn't be processed.\nMake sure that all document fields have been correctly set. This error happens usually when you are in review mode").format(count=len(items_error))
            self.srvdlg.show_error(title=_("Error processing documents"), body=body)


        wdir = self.webserver.get_directory()

        # Resources: TimelineJS Library
        ## Source
        timelinejs_path_source = os.path.join(ENV['LPATH']['PLUGINS'], 'MiAZTimelineJS', 'js', 'timeline.js')
        ## Target (path)
        timelinejs_path_target = os.path.join(wdir, 'MiAZTimelineJS', 'js', 'timeline.js')
        self.log.debug(f"TimelineJS Source: {timelinejs_path_source}")
        self.log.debug(f"TimelineJS Target: {timelinejs_path_target}")
        os.makedirs(os.path.dirname(timelinejs_path_target), exist_ok=True)
        shutil.copy(timelinejs_path_source, timelinejs_path_target)
        ## Target (url)
        host = self.webserver.get_host()
        port = self.webserver.get_port()
        timelinejs_url = f"http://{host}:{port}/MiAZTimelineJS/js/timeline.js"

        # Resources: TimelineJS CSS
        ## Source
        timelinecss_path_source = os.path.join(ENV['LPATH']['PLUGINS'], 'MiAZTimelineJS', 'css', 'timeline.css')

        ## Target (path)
        timelinecss_path_target = os.path.join(wdir, 'MiAZTimelineJS', 'css', 'timeline.css')
        self.log.debug(f"TimelineJS CSS Source: {timelinecss_path_source}")
        self.log.debug(f"TimelineJS CSS Target: {timelinecss_path_target}")
        os.makedirs(os.path.dirname(timelinecss_path_target), exist_ok=True)
        shutil.copytree(os.path.dirname(timelinecss_path_source), os.path.dirname(timelinecss_path_target), dirs_exist_ok=True)
        ## Target (url)
        timelinecss_url = f"http://{host}:{port}/MiAZTimelineJS/css/timeline.css"

        # Resources: JSON Data for TimelineJS
        timelinejsdata_path = os.path.join(wdir, 'MiAZTimelineJS', 'timelinejs.json')
        self.util.json_save(timelinejsdata_path, timelinejs_data)
        timelinejsdata_url = f"http://{host}:{port}/MiAZTimelineJS/timelinejs.json"


        # Resources: TimelineJS webpage
        ## Source
        TPL_TIMELINE=f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Timeline</title>
    <link rel="stylesheet" href="{timelinecss_url}" />
</head>
<body>
<div id="timeline-embed" style="width: 100%; height: 600px;"></div>

<script src="{timelinejs_url}"></script>
<script>
    var options = {{
            start_at_end: true,
            zoom_sequence: [0.5, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89],
            initial_zoom: 10,
            scale_factor: 1
        }}
    var timeline = new TL.Timeline('timeline-embed', "{timelinejsdata_url}", options);
</script>
</body>
</html>"""

        timelinejs_page = os.path.join(ENV['LPATH']['HTML'], 'MiAZTimelineJS', 'timeline.html')
        os.makedirs(os.path.dirname(timelinejs_page), exist_ok=True)
        with open(timelinejs_page, 'w') as fhtml:
            fhtml.write(TPL_TIMELINE)

        url = f"http://{host}:{port}/MiAZTimelineJS/timeline.html"
        stack = self.app.get_widget('stack')
        webbrowser = self.app.get_widget('webbrowser')
        self.log.debug(f"Loading {url}")
        webbrowser.load_url(url)
        stack.set_visible_child_name('page-webbrowser')
