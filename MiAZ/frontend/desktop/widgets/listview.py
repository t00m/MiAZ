#!/usr/bin/env python
# -*- coding: utf-8 -*-

from abc import abstractmethod

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository.GdkPixbuf import Pixbuf

class ListViewBase(Gtk.ListView):
    """ ListView base class, it setup the basic factory, selection model & data model
    handlers must be overloaded & implemented in a sub class
    """

    def __init__(self, model_cls):
        Gtk.ListView.__init__(self)
        # Use the signal Factory, so we can connect our own methods to setup
        self.factory = Gtk.SignalListItemFactory()
        # connect to Gtk.SignalListItemFactory signals
        # check https://docs.gtk.org/gtk4/class.SignalListItemFactory.html for details
        self.factory.connect('setup', self.on_factory_setup)
        self.factory.connect('bind', self.on_factory_bind)
        self.factory.connect('unbind', self.on_factory_unbind)
        self.factory.connect('teardown', self.on_factory_teardown)
        # Create data model, use our own class as elements
        self.set_factory(self.factory)
        self.store = self.setup_store(model_cls)
        # create a selection model containing our data model
        self.model = self.setup_model(self.store)
        self.model.connect('selection-changed', self.on_selection_changed)
        # set the selection model to the view
        self.set_model(self.model)

    def setup_model(self, store: Gio.ListModel) -> Gtk.SelectionModel:
        """  Setup the selection model to use in Gtk.ListView
        Can be overloaded in subclass to use another Gtk.SelectModel model
        """
        return Gtk.SingleSelection.new(store)

    @abstractmethod
    def setup_store(self, model_cls) -> Gio.ListModel:
        """ Setup the data model
        must be overloaded in subclass to use another Gio.ListModel
        """
        raise NotImplemented

    def add(self, elem):
        """ add element to the data model """
        self.store.append(elem)

    # Gtk.SignalListItemFactory signal callbacks
    # transfer to some some callback stubs, there can be overloaded in
    # a subclass.

    def on_factory_setup(self, widget, item: Gtk.ListItem):
        """ GtkSignalListItemFactory::setup signal callback

        Setup the widgets to go into the ListView """

        self.factory_setup(widget, item)

    def on_factory_bind(self, widget: Gtk.ListView, item: Gtk.ListItem):
        """ GtkSignalListItemFactory::bind signal callback

        apply data from model to widgets set in setup"""
        self.factory_bind(widget, item)

    def on_factory_unbind(self, widget, item: Gtk.ListItem):
        """ GtkSignalListItemFactory::unbind signal callback

        Undo the the binding done in ::bind if needed
        """
        self.factory_unbind(widget, item)

    def on_factory_teardown(self, widget, item: Gtk.ListItem):
        """ GtkSignalListItemFactory::setup signal callback

        Undo the creation done in ::setup if needed
        """
        self.factory_teardown(widget, item)

    def on_selection_changed(self, widget, position, n_items):
        # get the current selection (GtkBitset)
        selection = widget.get_selection()
        # the the first value in the GtkBitset, that contain the index of the selection in the data model
        # as we use Gtk.SingleSelection, there can only be one ;-)
        ndx = selection.get_nth(0)
        self.selection_changed(widget, ndx)

    # --------------------> abstract callback methods <--------------------------------
    # Implement these methods in your subclass

    @abstractmethod
    def factory_setup(self, widget: Gtk.ListView, item: Gtk.ListItem):
        """ Setup the widgets to go into the ListView (Overload in subclass) """
        pass

    @abstractmethod
    def factory_bind(self, widget: Gtk.ListView, item: Gtk.ListItem):
        """ apply data from model to widgets set in setup (Overload in subclass)"""
        pass

    @abstractmethod
    def factory_unbind(self, widget: Gtk.ListView, item: Gtk.ListItem):
        pass

    @abstractmethod
    def factory_teardown(self, widget: Gtk.ListView, item: Gtk.ListItem):
        pass

    @abstractmethod
    def selection_changed(self, widget, ndx):
        """ trigged when selecting in listview is changed
        ndx: is the index in the data store model that is selected
        """
        pass


class ListViewListStore(ListViewBase):
    """ ListView base with an Gio.ListStore as data model
    It can contain misc objects derived from GObject
    """

    def __init__(self, model_cls):
        super(ListViewListStore, self).__init__(model_cls)

    def setup_store(self, model_cls) -> Gio.ListModel:
        """ Setup the data model """
        return Gio.ListStore.new(model_cls)


class ColumnElem(GObject.GObject):
    """ custom data element for a ColumnView model (Must be based on GObject) """

    def __init__(self, name: str):
        super(ColumnElem, self).__init__()
        self.name = name

    def __repr__(self):
        return f'ColumnElem(name: {self.name})'


class ListElem(GObject.GObject):
    """ custom data element for a ListView model (Must be based on GObject) """

    def __init__(self, name: str, state: bool):
        super(ListElem, self).__init__()
        self.name = name
        self.state = state

    def __repr__(self):
        return f'ListElem(name: {self.name} state: {self.state})'

class ListElemRow(Gtk.ListBoxRow):
    """ custom data element for a ListView model (Must be based on GObject) """

    def __init__(self, name: str):
        super(ListElemRow, self).__init__()
        self.name = name

    def __repr__(self):
        return f'ListElemRow(name: {self.name})'


class MyListView(ListViewListStore):
    """ Custom ListView """
    n = 0

    def __init__(self, win: Gtk.ApplicationWindow):
        # Init ListView with store model class.
        super(MyListView, self).__init__(ListElem)
        self.win = win
        self.set_valign(Gtk.Align.FILL)
        # self.set_vexpand(True)
        # put some data into the model
        # ~ self.add(ListElem("One", True))
        # ~ self.add(ListElem("Two", False))
        # ~ self.add(ListElem("Three", True))
        # ~ self.add(ListElem("Four", False))

    def factory_setup(self, widget: Gtk.ListView, item: Gtk.ListItem):
        """ Gtk.SignalListItemFactory::setup signal callback (overloaded from parent class)

        Handles the creation widgets to put in the ListView
        """
        row = Gtk.ListBoxRow()
        label = Gtk.Label()
        row.set_child(label)
        # ~ label = Gtk.Label()
        # ~ label.set_halign(Gtk.Align.START)
        # ~ label.set_hexpand(True)
        # ~ label.set_margin_start(10)
        # ~ switch = Gtk.Switch()
        # ~ switch.set_halign(Gtk.Align.END)
        # ~ switch.set_margin_end(10)
        # ~ box.append(label)
        # ~ box.append(switch)
        item.set_child(row)

    def factory_bind(self, widget: Gtk.ListView, item: Gtk.ListItem):
        """ Gtk.SignalListItemFactory::bind signal callback (overloaded from parent class)

        Handles adding data for the model to the widgets created in setup
        """
        # get the Gtk.Box stored in the ListItem
        row = item.get_child()
        # get the model item, connected to current ListItem
        data = item.get_item()
        print("%s > %s" % (item, data))
        # get the Gtk.Label (first item in box)
        label = row.get_first_child()
        label.set_text(data.name)
        # get the Gtk.Switch (next sibling to the Label)
        # ~ switch = label.get_next_sibling()
        # Update Gtk.Label with data from model item
        # ~ label.set_text(data.name)
        # Update Gtk.Switch with data from model item
        # ~ switch.set_state(data.state)
        # connect switch to handler, so we can handle changes
        # ~ switch.connect('state-set', self.switch_changed, item.get_position())
        label.set_text("Row: %d" % self.n)
        item.set_child(row)
        self.n += 1

    def factory_unbind(self, widget: Gtk.ListView, item: Gtk.ListItem):
        """ Gtk.SignalListItemFactory::unbind signal callback (overloaded from parent class) """
        pass

    def factory_teardown(self, widget: Gtk.ListView, item: Gtk.ListItem):
        """ Gtk.SignalListItemFactory::teardown signal callback (overloaded from parent class """
        pass

    def selection_changed(self, widget, ndx: int):
        """ trigged when selecting in listview is changed"""
        markup = self.win._get_text_markup(
            f'Row {ndx} was selected ( {self.store[ndx]} )')
        self.win.page4_label.set_markup(markup)

    def switch_changed(self, widget, state: bool, pos: int):
        # update the data model, with current state
        elem = self.store[pos]
        elem.state = state
        markup = self.win._get_text_markup(
            f'switch in row {pos}, changed to {state}')
        self.win.page4_label.set_markup(markup)
