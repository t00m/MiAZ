# File: cardview.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: The workspace as contact cards, one per party

from gettext import gettext as _

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from contacts import parties as partieslib
from contacts.card import ContactCard

# A card is wide, so a screen holds few of them. More columns than this and
# the cards stop being readable.
MAX_COLUMNS = 4

# What one card asks for, in pixels.
CARD_WIDTH = 320


class PartyItem(GObject.Object):
    """One party, wrapped so a Gio.ListStore can hold it."""
    __gtype_name__ = 'MiAZContactsPartyItem'

    def __init__(self, party):
        super().__init__()
        self.party = party

    @property
    def key(self):
        return self.party.key


class MiAZContactsView(Gtk.Box):
    """Pure view over the filtered set: one card per distinct party.

    It carries no model unless it is the view on screen, the same contract the
    grid, the timeline and the conversations follow. An Adw.ViewStack measures
    the pages it is not showing, so a view that built cards while hidden would
    read every contact file for nothing.
    """
    __gtype_name__ = 'MiAZContactsView'

    def __init__(self, app, plugin, model=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.plugin = plugin
        self.log = plugin.log
        self._showing = False
        self._rebuild_id = None
        if model is None:
            model = self.app.get_widget('workspace-view').filter_model
        self.model = model
        self.store = Gio.ListStore(item_type=PartyItem)
        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', self._on_setup)
        factory.connect('bind', self._on_bind)
        self.gridview = Gtk.GridView(factory=factory)
        self.gridview.set_max_columns(MAX_COLUMNS)
        self.gridview.set_min_columns(1)
        self.gridview.add_css_class('miaz-contacts')
        scrwin = Gtk.ScrolledWindow()
        scrwin.set_hexpand(True)
        scrwin.set_vexpand(True)
        scrwin.set_child(self.gridview)
        self.append(scrwin)
        self.model.connect('items-changed', self._on_items_changed)

    def set_active(self, active):
        """Say whether this is the view on screen. Inactive means no model."""
        if active == self._showing:
            return
        self._showing = active
        if active:
            self.refresh()
            self.gridview.set_model(Gtk.NoSelection(model=self.store))
        else:
            self._cancel_rebuild()
            self.gridview.set_model(None)
            self.store.remove_all()

    def get_parties(self):
        """The parties currently on screen, in card order."""
        return [self.store.get_item(index).party
                for index in range(self.store.get_n_items())]

    def refresh(self):
        """Fold the filtered documents into one entry per party."""
        self.store.remove_all()
        for party in partieslib.parties(self._items()):
            self.store.append(PartyItem(party))

    def _items(self):
        return [self.model.get_item(index)
                for index in range(self.model.get_n_items())]

    def _cancel_rebuild(self):
        if self._rebuild_id is not None:
            GLib.source_remove(self._rebuild_id)
            self._rebuild_id = None

    def _on_items_changed(self, *args):
        # The store cannot be rebuilt inside items-changed: GTK is halfway
        # through updating the cells that list it.
        if not self._showing or self._rebuild_id is not None:
            return
        self._rebuild_id = GLib.idle_add(self._rebuild)

    def _rebuild(self):
        self._rebuild_id = None
        if self._showing:
            self.refresh()
        return GLib.SOURCE_REMOVE

    def _on_setup(self, factory, list_item):
        card = ContactCard()
        card.connect('show-documents', self._on_show)
        card.connect('edit-contact', self._on_edit)
        list_item.set_child(card)

    def _on_bind(self, factory, list_item):
        item = list_item.get_item()
        card = list_item.get_child()
        card.set_size_request(CARD_WIDTH, -1)
        card.update(item.party, self.plugin.get_store().get(item.key))

    def _on_show(self, card, key):
        """Narrow the workspace to the documents this party is named in."""
        workspace = self.app.get_widget('workspace')
        if workspace is None:
            return
        documents = partieslib.documents_for(key, self._items())
        party = next((one for one in self.get_parties() if one.key == key), None)
        label = party.description if party is not None else key
        workspace.show_documents(documents, label=_('Documents of {name}').format(name=label))

    def _on_edit(self, card, key):
        party = next((one for one in self.get_parties() if one.key == key), None)
        self.plugin.open_editor(key, party.description if party is not None else '')
