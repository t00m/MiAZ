import gi
from gi.repository import GObject

class MiAZModel(GObject.Object):
    """Custom data model for MiAZ use cases"""
    __gtype_name__ = 'MiAZModel'

    def __init__(self, id: str, title: str = '', subtitle:str = '', active: bool = False, icon: str = ''):
        super().__init__()

        self._id = id
        self._title = title
        self._subtitle = subtitle
        self._active = active
        self._icon = icon

    @GObject.Property
    def id(self):
        return self._id

    @GObject.Property
    def title(self):
        return self._title

    @GObject.Property
    def subtitle(self):
        return self._subtitle

    @GObject.Property(type=bool, default=False)
    def active(self):
        return self._active

    @active.setter
    def active(self, active):
        self._active = active

    @GObject.Property
    def icon(self):
        return self._icon

row = MiAZModel(id='uno')
for prop in row.list_properties():
    print("%s > %s > %s > %s" % (prop, type(prop), prop.name, prop.flags))
