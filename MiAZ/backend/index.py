
"""
# File: index.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: In-memory index of the repository documents
"""

import os

from gi.repository import GObject

from MiAZ.backend.duplicates import find_duplicates
from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import Field, MiAZItem
from MiAZ.backend.util import humanize_value

# Config name and position in the 7-field filename. Concept has no controlled
# vocabulary, so it is parsed but never validated against a config.
KEY_FIELDS = [
    ('Date', 0),
    ('Country', 1),
    ('Group', 2),
    ('SentBy', 3),
    ('Purpose', 4),
    ('Concept', 5),
    ('SentTo', 6),
]

CONCEPT_INDEX = 5
DATE_INDEX = 0

CACHED_CONFIGS = ('Date', 'Country', 'Group', 'SentBy', 'SentTo', 'Purpose')


class MiAZDocumentIndex(GObject.GObject):
    """In-memory view of the repository. No GTK.

    Owns the only path from a filename to a MiAZItem. The full scan and the
    single-file update both go through build_item, so they cannot disagree.
    """

    __gtype_name__ = 'MiAZDocumentIndex'
    __gsignals__ = {
        'index-loaded': (GObject.SignalFlags.RUN_LAST, None, ()),
        'index-changed': (GObject.SignalFlags.RUN_LAST, None, (object,)),
        'duplicates-scanned': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.log = MiAZLog('MiAZ.Index')
        self._items = {}
        self._paths = {}
        self._invalid = []
        self._field_index = {ft: {} for ft in Field}
        # Documents with identical content, filled by scan_duplicates. Not
        # computed until something asks: the scan reads files, the rest does not.
        self._duplicates = {}
        self._duplicates_stale = True
        self.cache = {name: {} for name in CACHED_CONFIGS}

    def reload(self):
        """Rescan the repository and rebuild every derived structure."""
        util = self.app.get_service('util')
        repository = self.app.get_service('repo')
        try:
            docs = util.get_files(repository.docs)
        except (KeyError, TypeError, OSError) as error:
            self.log.warning(f"Cannot list the repository: {error}")
            docs = []

        self._items = {}
        self._paths = {}
        self._invalid = []
        self._field_index = {ft: {} for ft in Field}
        for path in docs:
            self._add(path)
        self._invalidate_duplicates()
        self.log.debug(f"Index loaded: {len(self._items)} documents")
        self.emit('index-loaded')

    def _add(self, path):
        """Index one document path. Returns the item."""
        util = self.app.get_service('util')
        basename = os.path.basename(path)
        item = self.build_item(path)
        self._items[basename] = item
        self._paths[basename] = path
        if not item.valid:
            self._invalid.append(basename)
        fields = util.get_fields(path)
        if len(fields) == 7:
            for field_type, idx in Field.items():
                self._field_index[field_type].setdefault(fields[idx], []).append(path)
        return item

    def _remove(self, basename):
        """Drop one document from every structure. Returns True if it was there."""
        if basename not in self._items:
            return False
        util = self.app.get_service('util')
        path = self._paths.pop(basename)
        del self._items[basename]
        if basename in self._invalid:
            self._invalid.remove(basename)
        fields = util.get_fields(basename)
        if len(fields) == 7:
            for field_type, idx in Field.items():
                bucket = self._field_index[field_type].get(fields[idx])
                if not bucket:
                    continue
                if path in bucket:
                    bucket.remove(path)
                if not bucket:
                    del self._field_index[field_type][fields[idx]]
        return True

    def apply_change(self, path, event, other=None):
        """Apply one filesystem event.

        Returns True when the index now reflects the change, False when the
        caller should fall back to a full reload. Emits 'index-changed' with the
        list of (action, payload) operations, where payload is a MiAZItem for
        'add' and 'update' and a filename for 'remove'.
        """
        if not self._in_repository(path):
            return False

        if event in ('changed', 'attribute-changed'):
            # The row is derived from the filename, so neither alters it. The
            # duplicate map is derived from the bytes, so 'changed' does.
            if event == 'changed':
                self._invalidate_duplicates()
            return True

        if event in ('deleted', 'moved-out'):
            basename = os.path.basename(path)
            if self._remove(basename):
                self._invalidate_duplicates()
                self.emit('index-changed', [('remove', basename)])
            return True

        if event == 'renamed':
            if not other or not self._in_repository(other):
                return False
            if not self._is_normalizable(other):
                return False
            basename = os.path.basename(path)
            self._remove(basename)
            item = self._add(other)
            # A rename moves no bytes, so a scan already made is still right.
            self._rename_duplicate(basename, os.path.basename(other))
            self.emit('index-changed', [('remove', basename), ('add', item)])
            return True

        if event in ('created', 'moved-in', 'changes-done-hint'):
            if not self._is_normalizable(path):
                return False
            basename = os.path.basename(path)
            action = 'update' if self._remove(basename) else 'add'
            item = self._add(path)
            self._invalidate_duplicates()
            self.emit('index-changed', [(action, item)])
            return True

        return False

    def _is_normalizable(self, path):
        """False when the name still has to be normalized on disk.

        Such a document has to go through the full scan, which is what renames
        it. Applying it incrementally would let the caller skip that scan and
        leave the file with its original name.
        """
        util = self.app.get_service('util')
        return util.filename_validate(path)

    def _in_repository(self, path):
        """True when path is a visible file directly in the repository root."""
        repository = self.app.get_service('repo')
        if repository is None or not repository.docs:
            return False
        basename = os.path.basename(path)
        if basename.startswith('.'):
            return False
        return os.path.dirname(path) == os.path.normpath(repository.docs)

    def invalidate_cache(self, config_name=None, key=None):
        """Drop cached descriptions.

        With no arguments every entry goes. With a config name only that config
        is cleared. With both, one entry. The workspace uses the last form: the
        'used-updated' signal says which keys changed, so only those go.
        """
        if config_name is None:
            for entries in self.cache.values():
                entries.clear()
            return
        entries = self.cache.get(config_name)
        if entries is None:
            return
        if key is None:
            entries.clear()
        else:
            entries.pop(key, None)

    def documents(self):
        """Every indexed item, in scan order."""
        return list(self._items.values())

    def document(self, item_id):
        """One item by filename, or None."""
        return self._items.get(item_id)

    def scan_duplicates(self):
        """Find documents with identical content and emit when done.

        Reads every file that shares a size with another, so it belongs in a
        worker: about 0.9s for 1336 documents. Touches no GTK.
        """
        paths = list(self._paths.values())
        found = find_duplicates(paths)
        self._duplicates = {
            os.path.basename(path): sorted(os.path.basename(o) for o in others)
            for path, others in found.items()
        }
        self._duplicates_stale = False
        self.log.debug(f"Duplicates: {len(self._duplicates)} documents with a twin")
        self.emit('duplicates-scanned')

    def duplicates_of(self, basename):
        """Documents with the same content as this one, or [] when there are
        none, when it is unknown, or when nothing has been scanned yet."""
        return list(self._duplicates.get(basename, []))

    def duplicates_of_any(self):
        """True when the last scan found at least one document with a twin."""
        return bool(self._duplicates)

    def duplicates_stale(self):
        """True when the map needs rebuilding before it can be trusted."""
        return self._duplicates_stale

    def _invalidate_duplicates(self):
        self._duplicates = {}
        self._duplicates_stale = True

    def _rename_duplicate(self, old, new):
        """Follow a rename through the map, keeping a scan that is still valid."""
        if self._duplicates_stale or old not in self._duplicates:
            return
        self._duplicates[new] = self._duplicates.pop(old)
        for others in self._duplicates.values():
            if old in others:
                others[others.index(old)] = new
                others.sort()

    def pending(self):
        """Items that fail validation against the enabled config."""
        return [item for item in self._items.values() if not item.active]

    def invalid(self):
        """Filenames that do not split into seven non-empty fields."""
        return list(self._invalid)

    def field_index(self):
        """{field model: {value: [document paths]}}."""
        return self._field_index

    def concepts(self):
        """(active, inactive) sorted concept lists, for the rename dialog."""
        active = set()
        inactive = set()
        for item in self._items.values():
            target = active if item.active else inactive
            target.add(item.subtitle)
        return sorted(active), sorted(inactive)

    def build_item(self, filename):
        """Return the MiAZItem for one document name.

        Accepts a bare filename or a full path. A name that does not split into
        seven non-empty fields still produces an item, inactive and carrying the
        raw name, so the caller always gets a row to show.
        """
        util = self.app.get_service('util')
        basename = os.path.basename(filename)
        doc, ext = util.filename_details(filename)
        fields = util.get_fields(filename)
        valid = len(fields) == 7 and all(fields)

        if len(fields) != 7:
            return MiAZItem(
                id=basename,
                title=doc,
                subtitle='_'.join(fields),
                extension=ext,
                active=False,
                valid=False)

        desc = {name: '' for name, _idx in KEY_FIELDS}
        active = valid
        for name, idx in KEY_FIELDS:
            if idx == CONCEPT_INDEX:
                continue
            key = fields[idx]
            if not key:
                active = False
                continue
            if idx == DATE_INDEX:
                active &= self._describe_date(desc, name, key)
            else:
                self._describe_value(desc, name, key)
                config = self.app.get_config(name)
                active &= config.exists_used(key=key)

        return MiAZItem(
            id=basename,
            date=fields[0], date_dsc=desc['Date'],
            country=fields[1], country_dsc=desc['Country'],
            group=fields[2], group_dsc=desc['Group'],
            sentby_id=fields[3], sentby_dsc=desc['SentBy'],
            purpose=fields[4], purpose_dsc=desc['Purpose'],
            title=doc,
            subtitle=fields[CONCEPT_INDEX].replace('_', ' '),
            sentto_id=fields[6], sentto_dsc=desc['SentTo'],
            extension=ext,
            active=active,
            valid=valid)

    def _describe_date(self, desc, name, key):
        """Fill the human date. Returns False when the date cannot be parsed."""
        try:
            desc[name] = self.cache[name][key]
            return True
        except KeyError:
            pass
        util = self.app.get_service('util')
        human = util.filename_date_human_simple(key)
        if human is None:
            desc[name] = ''
            return False
        desc[name] = human
        self.cache[name][key] = human
        return True

    def _describe_value(self, desc, name, key):
        """Fill the human label for a controlled-vocabulary field."""
        try:
            desc[name] = self.cache[name][key]
            return
        except KeyError:
            pass
        config = self.app.get_config(name)
        description = config.get(key)
        if description is None:
            description = key
        desc[name] = humanize_value(name, description)
        self.cache[name][key] = desc[name]
