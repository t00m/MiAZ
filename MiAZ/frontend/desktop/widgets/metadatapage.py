# File: metadatapage.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: The Metadata tab of the Repository Settings dialog

from MiAZ.backend.log import MiAZLog
from MiAZ.frontend.desktop.widgets.sidebarstack import MiAZSidebarStack


class MiAZMetadataPage(MiAZSidebarStack):
    """The repository vocabularies, one list on the left and one view shown.

    They used to be five tabs across the top of the dialog, which left no room
    for a sixth: the plugins that own a vocabulary of their own had to put it
    behind a button somewhere else. A list takes as many as it is given.

    The list and stack themselves are MiAZSidebarStack, shared with the
    Settings tab. What is left here is what a vocabulary list adds to that:
    where the entries come from.
    """
    __gtype_name__ = 'MiAZMetadataPage'

    def __init__(self, app):
        super().__init__(app)
        self.log = MiAZLog('MiAZ.MetadataPage')
        self.app.add_widget('repository-settings-page-metadata', self)

    def add_view(self, name, title, icon_name, widget):
        """Add one vocabulary to the list and its view to the stack."""
        self.add_page(name, title, icon_name, widget)

    def get_view_names(self) -> list:
        return self.get_page_names()

    def show_view(self, name):
        self.show_page(name)

    def add_plugin_views(self):
        """Add the vocabularies plugins own, after the built-in ones."""
        registry = self.app.get_service('plugin-system').settings
        for _owner, name, title, icon_name, factory in registry.views():
            if self.has_page(name):
                continue
            try:
                widget = factory()
            except Exception as error:
                self.log.error(f"Metadata view {name}: {error}")
                continue
            if widget is not None:
                self.add_view(name, title, icon_name, widget)
