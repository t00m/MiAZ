#!/usr/bin/python3

"""
Tests for MiAZ.backend.index — the document index.

Runs without a display: GObject/Gio only, no GTK/Adw. This is the point of the
module. The parse it owns used to live inside MiAZWorkspace, a Gtk.Box, and had
no tests at all.
"""

import os
import threading

import gi
gi.require_version('GLib', '2.0')
gi.require_version('Gio', '2.0')

from gi.repository import GLib
import pytest

from MiAZ.backend.index import MiAZDocumentIndex
from MiAZ.backend.util import MiAZUtil


class MockConfig:
    """Stand-in for a MiAZConfig entry.

    The index only calls get() and exists_used(). `used` holds the enabled
    values for the repository, mapping code to description.
    """

    def __init__(self, used=None):
        self._used = dict(used or {})
        self.get_calls = 0

    def get(self, key):
        self.get_calls += 1
        return self._used.get(key)

    def exists_used(self, key):
        return key in self._used


class MockRepository:
    def __init__(self, docs, conf=None):
        self.docs = docs
        self.conf = conf or os.path.join(docs, '.conf')


class MockApp:
    """Stand-in for MiAZApp with the three lookups the index performs."""

    def __init__(self, docs_dir, configs=None):
        self._configs = configs or {}
        self._util = MiAZUtil(self)
        self._repo = MockRepository(docs_dir)

    def get_config(self, name):
        return self._configs.get(name)

    def get_service(self, name):
        if name == 'util':
            return self._util
        if name == 'repo':
            return self._repo
        return None


def default_configs():
    """Config set where every value used by the sample filenames is enabled."""
    return {
        'Date': MockConfig(),
        'Country': MockConfig({'ES': 'Spain'}),
        'Group': MockConfig({'HOU': 'Housing'}),
        'SentBy': MockConfig({'BANK': 'The Bank'}),
        'Purpose': MockConfig({'INV': 'Invoice'}),
        'Concept': MockConfig(),
        'SentTo': MockConfig({'JOHNDOE': 'John Doe'}),
    }


@pytest.fixture
def index(tmp_path):
    return MiAZDocumentIndex(MockApp(str(tmp_path), default_configs()))


def touch(tmp_path, name):
    path = tmp_path / name
    path.write_text('x')
    return str(path)


VALID = '20240315-ES-HOU-BANK-INV-Q1invoice-JOHNDOE.pdf'


# ---------------------------------------------------------------------------
# build_item
# ---------------------------------------------------------------------------

def test_build_item_splits_the_seven_fields(index):
    item = index.build_item(VALID)
    assert item.id == VALID
    assert item.date == '20240315'
    assert item.country == 'ES'
    assert item.group == 'HOU'
    assert item.sentby_id == 'BANK'
    assert item.purpose == 'INV'
    assert item.subtitle == 'Q1invoice'
    assert item.sentto_id == 'JOHNDOE'
    assert item.extension == 'pdf'


def test_build_item_is_active_when_every_value_is_enabled(index):
    assert index.build_item(VALID).active is True


def test_build_item_fills_descriptions_from_config(index):
    item = index.build_item(VALID)
    assert item.country_dsc == 'Spain'
    assert item.group_dsc == 'Housing'
    assert item.sentby_dsc == 'The Bank'
    assert item.purpose_dsc == 'Invoice'
    assert item.sentto_dsc == 'John Doe'


def test_build_item_renders_the_date_description(index):
    assert index.build_item(VALID).date_dsc == '15/03/2024'


def test_build_item_replaces_underscores_in_concept(index):
    item = index.build_item('20240315-ES-HOU-BANK-INV-first_quarter-JOHNDOE.pdf')
    assert item.subtitle == 'first quarter'


def test_build_item_is_inactive_when_a_value_is_not_enabled(index):
    item = index.build_item('20240315-XX-HOU-BANK-INV-Q1invoice-JOHNDOE.pdf')
    assert item.active is False


def test_build_item_falls_back_to_the_code_when_config_has_no_description(index):
    item = index.build_item('20240315-XX-HOU-BANK-INV-Q1invoice-JOHNDOE.pdf')
    assert item.country_dsc == 'XX'


def test_build_item_is_inactive_when_the_date_is_unparseable(index):
    item = index.build_item('NODATE00-ES-HOU-BANK-INV-Q1invoice-JOHNDOE.pdf')
    assert item.active is False
    assert item.date_dsc == ''


def test_build_item_is_inactive_when_a_field_is_empty(index):
    item = index.build_item('20240315--HOU-BANK-INV-Q1invoice-JOHNDOE.pdf')
    assert item.active is False


def test_build_item_handles_a_name_with_fewer_than_seven_fields(index):
    """The old parse raised IndexError here and fell into a fallback branch.
    Same result, without the exception: an inactive item carrying the raw name.
    """
    item = index.build_item('holiday_photo.jpg')
    assert item.active is False
    assert item.id == 'holiday_photo.jpg'
    assert item.subtitle == 'holiday_photo'


def test_build_item_accepts_a_full_path_and_keeps_the_basename_as_id(tmp_path, index):
    item = index.build_item(str(tmp_path / VALID))
    assert item.id == VALID


def test_build_item_caches_descriptions_between_calls(index):
    config = index.app.get_config('Country')
    index.build_item(VALID)
    calls_after_first = config.get_calls
    index.build_item('20240316-ES-HOU-BANK-INV-other-JOHNDOE.pdf')
    assert config.get_calls == calls_after_first


def test_build_item_marks_a_structurally_valid_name(index):
    assert index.build_item(VALID).valid is True


def test_build_item_marks_a_structurally_invalid_name(index):
    assert index.build_item('holiday_photo.jpg').valid is False


# ---------------------------------------------------------------------------
# reload
# ---------------------------------------------------------------------------

def test_reload_lists_the_repository_documents(tmp_path, index):
    touch(tmp_path, VALID)
    touch(tmp_path, '20240316-ES-HOU-BANK-INV-second-JOHNDOE.pdf')
    index.reload()
    assert len(index.documents()) == 2


def test_reload_skips_hidden_files(tmp_path, index):
    touch(tmp_path, VALID)
    touch(tmp_path, '.hidden')
    index.reload()
    assert [item.id for item in index.documents()] == [VALID]


def test_reload_emits_index_loaded(tmp_path, index):
    touch(tmp_path, VALID)
    seen = []
    index.connect('index-loaded', lambda *a: seen.append(True))
    index.reload()
    assert seen == [True]


def test_reload_twice_does_not_duplicate(tmp_path, index):
    touch(tmp_path, VALID)
    index.reload()
    index.reload()
    assert len(index.documents()) == 1


def test_reload_on_a_missing_directory_yields_no_documents(tmp_path):
    app = MockApp(str(tmp_path / 'gone'), default_configs())
    index = MiAZDocumentIndex(app)
    index.reload()
    assert index.documents() == []


def test_pending_returns_only_inactive_documents(tmp_path, index):
    touch(tmp_path, VALID)
    touch(tmp_path, '20240316-XX-HOU-BANK-INV-unknown-JOHNDOE.pdf')
    index.reload()
    pending = index.pending()
    assert [item.country for item in pending] == ['XX']


def test_invalid_returns_structurally_broken_names(tmp_path, index):
    touch(tmp_path, VALID)
    touch(tmp_path, 'holiday_photo.jpg')
    index.reload()
    assert index.invalid() == ['holiday_photo.jpg']


def test_invalid_includes_a_name_with_an_empty_field(tmp_path, index):
    touch(tmp_path, '20240315--HOU-BANK-INV-Q1invoice-JOHNDOE.pdf')
    index.reload()
    assert len(index.invalid()) == 1


def test_field_index_maps_a_value_to_its_documents(tmp_path, index):
    touch(tmp_path, VALID)
    touch(tmp_path, '20240316-ES-HOU-BANK-INV-second-JOHNDOE.pdf')
    index.reload()
    from MiAZ.backend.models import Country
    assert len(index.field_index()[Country]['ES']) == 2


def test_field_index_ignores_names_that_do_not_split_into_seven(tmp_path, index):
    touch(tmp_path, 'holiday_photo.jpg')
    index.reload()
    from MiAZ.backend.models import Country
    assert index.field_index()[Country] == {}


def test_concepts_are_split_by_active_state(tmp_path, index):
    touch(tmp_path, VALID)
    touch(tmp_path, '20240316-XX-HOU-BANK-INV-notenabled-JOHNDOE.pdf')
    index.reload()
    active, inactive = index.concepts()
    assert active == ['Q1invoice']
    assert inactive == ['notenabled']


def test_document_returns_one_item_by_id(tmp_path, index):
    touch(tmp_path, VALID)
    index.reload()
    assert index.document(VALID).country == 'ES'


def test_document_returns_none_for_an_unknown_id(index):
    assert index.document('nope.pdf') is None


# ---------------------------------------------------------------------------
# apply_change
# ---------------------------------------------------------------------------

NEW = '20240316-ES-HOU-BANK-INV-second-JOHNDOE.pdf'


def test_apply_change_created_adds_the_document(tmp_path, index):
    index.reload()
    path = touch(tmp_path, NEW)
    assert index.apply_change(path, 'created') is True
    assert index.document(NEW) is not None


def test_apply_change_deleted_removes_the_document(tmp_path, index):
    path = touch(tmp_path, VALID)
    index.reload()
    os.unlink(path)
    assert index.apply_change(path, 'deleted') is True
    assert index.document(VALID) is None


def test_apply_change_renamed_swaps_the_document(tmp_path, index):
    old = touch(tmp_path, VALID)
    index.reload()
    new = touch(tmp_path, NEW)
    os.unlink(old)
    assert index.apply_change(old, 'renamed', other=new) is True
    assert index.document(VALID) is None
    assert index.document(NEW) is not None


def test_apply_change_deleted_for_an_unknown_file_emits_nothing(tmp_path, index):
    """The view must not be told to remove a row it never had, or the caller's
    document count drifts below the real one.
    """
    index.reload()
    seen = []
    index.connect('index-changed', lambda _idx, ops: seen.append(ops))
    assert index.apply_change(str(tmp_path / NEW), 'deleted') is True
    assert seen == []


def test_apply_change_renamed_without_a_target_is_not_applied(tmp_path, index):
    path = touch(tmp_path, VALID)
    index.reload()
    assert index.apply_change(path, 'renamed') is False


def test_apply_change_content_edit_is_a_noop(tmp_path, index):
    path = touch(tmp_path, VALID)
    index.reload()
    assert index.apply_change(path, 'changed') is True
    assert len(index.documents()) == 1


def test_apply_change_created_twice_does_not_duplicate(tmp_path, index):
    path = touch(tmp_path, VALID)
    index.reload()
    index.apply_change(path, 'created')
    assert len(index.documents()) == 1


def test_apply_change_ignores_an_unknown_event(tmp_path, index):
    path = touch(tmp_path, VALID)
    index.reload()
    assert index.apply_change(path, 'something-else') is False


def test_apply_change_ignores_hidden_files(tmp_path, index):
    index.reload()
    path = touch(tmp_path, '.hidden')
    assert index.apply_change(path, 'created') is False


def test_apply_change_ignores_files_outside_the_repository(tmp_path, index):
    index.reload()
    outside = tmp_path / 'sub'
    outside.mkdir()
    path = outside / NEW
    path.write_text('x')
    assert index.apply_change(str(path), 'created') is False


def test_apply_change_emits_index_changed_with_the_operations(tmp_path, index):
    index.reload()
    path = touch(tmp_path, NEW)
    seen = []
    index.connect('index-changed', lambda _idx, ops: seen.append(ops))
    index.apply_change(path, 'created')
    assert seen and seen[0][0][0] == 'add'


def test_apply_change_updates_the_field_index(tmp_path, index):
    index.reload()
    path = touch(tmp_path, NEW)
    index.apply_change(path, 'created')
    from MiAZ.backend.models import Date
    assert '20240316' in index.field_index()[Date]


def test_apply_change_drops_the_field_index_entry_on_delete(tmp_path, index):
    path = touch(tmp_path, VALID)
    index.reload()
    os.unlink(path)
    index.apply_change(path, 'deleted')
    from MiAZ.backend.models import Date
    assert '20240315' not in index.field_index()[Date]


def test_apply_change_keeps_concepts_fresh(tmp_path, index):
    """The old incremental path never refreshed the concept lists, so the
    rename dialog kept offering concepts from the last full scan.
    """
    index.reload()
    path = touch(tmp_path, NEW)
    index.apply_change(path, 'created')
    active, _inactive = index.concepts()
    assert 'second' in active


def test_apply_change_handles_a_document_with_a_pending_name(tmp_path, index):
    """Seven non-empty fields but a value the config does not enable. The
    document is indexed and flagged for review, no full rescan needed.
    """
    index.reload()
    path = touch(tmp_path, '20240316-XX-HOU-BANK-INV-pending-JOHNDOE.pdf')
    assert index.apply_change(path, 'created') is True
    assert len(index.pending()) == 1


def test_apply_change_asks_for_a_full_reload_on_an_invalid_name(tmp_path, index):
    """A name that does not split into seven fields must go through the full
    scan, which is what normalizes it on disk. Returning True here would skip
    that rescan and leave the file un-normalized.
    """
    index.reload()
    path = touch(tmp_path, 'holiday_photo.jpg')
    assert index.apply_change(path, 'created') is False


def test_apply_change_asks_for_a_full_reload_when_a_rename_lands_invalid(tmp_path, index):
    old = touch(tmp_path, VALID)
    index.reload()
    new = touch(tmp_path, 'holiday_photo.jpg')
    os.unlink(old)
    assert index.apply_change(old, 'renamed', other=new) is False


# ---------------------------------------------------------------------------
# The drift guard: one parse, two entry points
# ---------------------------------------------------------------------------

def _snapshot(items):
    return sorted(
        (i.id, i.date, i.date_dsc, i.country, i.country_dsc, i.group,
         i.group_dsc, i.sentby_id, i.sentby_dsc, i.purpose, i.purpose_dsc,
         i.subtitle, i.sentto_id, i.sentto_dsc, i.extension, i.active, i.valid)
        for i in items)


def test_incremental_and_full_scan_agree(tmp_path, index):
    """Every document the incremental path accepts must come out identical to
    what the full scan produces. This is the guard the two old parses lacked.
    """
    names = [
        VALID,
        NEW,
        '20240317-XX-HOU-BANK-INV-notenabled-JOHNDOE.pdf',
        '20240318-ES-HOU-BANK-INV-two_words-JOHNDOE.pdf',
        'NODATE00-ES-HOU-BANK-INV-baddate-JOHNDOE.pdf',
    ]
    index.reload()
    for name in names:
        assert index.apply_change(touch(tmp_path, name), 'created') is True
    incremental = _snapshot(index.documents())

    index.reload()
    full = _snapshot(index.documents())

    assert incremental == full


def test_names_the_incremental_path_rejects_still_land_in_a_full_scan(tmp_path, index):
    """The rejected ones are not lost: the full scan picks them up, which is
    also where they get normalized on disk.
    """
    touch(tmp_path, 'holiday_photo.jpg')
    touch(tmp_path, '20240318--HOU-BANK-INV-emptyfield-JOHNDOE.pdf')
    index.reload()
    assert len(index.documents()) == 2
    assert len(index.invalid()) == 2


# ---------------------------------------------------------------------------
# invalidate_cache
# ---------------------------------------------------------------------------

def test_invalidate_cache_drops_one_entry(index):
    index.build_item(VALID)
    index.invalidate_cache('Country', 'ES')
    assert 'ES' not in index.cache['Country']
    assert '20240315' in index.cache['Date']


def test_invalidate_cache_without_a_key_drops_one_config(index):
    index.build_item(VALID)
    index.invalidate_cache('Country')
    assert index.cache['Country'] == {}
    assert '20240315' in index.cache['Date']


def test_invalidate_cache_without_arguments_drops_everything(index):
    index.build_item(VALID)
    index.invalidate_cache()
    assert all(entries == {} for entries in index.cache.values())


def test_invalidate_cache_ignores_an_unknown_config(index):
    index.build_item(VALID)
    index.invalidate_cache('Nonexistent', 'X')
    assert 'ES' in index.cache['Country']


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------

TWIN_A = '20240315-ES-HOU-BANK-INV-first-JOHNDOE.pdf'
TWIN_B = '20240316-ES-HOU-BANK-INV-second-JOHNDOE.pdf'
LONELY = '20240317-ES-HOU-BANK-INV-alone-JOHNDOE.pdf'


def write(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content)
    return str(path)


def loaded_with_twins(index, tmp_path):
    """A repository holding one duplicate pair and one unique document."""
    write(tmp_path, TWIN_A, 'identical')
    write(tmp_path, TWIN_B, 'identical')
    write(tmp_path, LONELY, 'something else entirely')
    index.reload()
    index.scan_duplicates()
    return index


def test_duplicates_are_found_by_content_not_by_name(index, tmp_path):
    loaded_with_twins(index, tmp_path)
    assert index.duplicates_of(TWIN_A) == [TWIN_B]
    assert index.duplicates_of(TWIN_B) == [TWIN_A]
    assert index.duplicates_of(LONELY) == []


def test_a_document_that_is_not_indexed_has_no_duplicates(index, tmp_path):
    loaded_with_twins(index, tmp_path)
    assert index.duplicates_of('never-heard-of-it.pdf') == []


def test_duplicates_are_stale_until_scanned(index, tmp_path):
    write(tmp_path, TWIN_A, 'identical')
    write(tmp_path, TWIN_B, 'identical')
    index.reload()
    assert index.duplicates_stale() is True
    assert index.duplicates_of(TWIN_A) == [], 'answered before scanning'
    index.scan_duplicates()
    assert index.duplicates_stale() is False


def test_a_reload_makes_them_stale_again(index, tmp_path):
    loaded_with_twins(index, tmp_path)
    index.reload()
    assert index.duplicates_stale() is True


def test_adding_a_document_makes_them_stale(index, tmp_path):
    loaded_with_twins(index, tmp_path)
    path = write(tmp_path, '20240318-ES-HOU-BANK-INV-new-JOHNDOE.pdf', 'identical')
    index.apply_change(path, 'created')
    assert index.duplicates_stale() is True, 'a new file could duplicate anything'


def test_deleting_a_document_makes_them_stale(index, tmp_path):
    loaded_with_twins(index, tmp_path)
    os.remove(os.path.join(str(tmp_path), TWIN_B))
    index.apply_change(os.path.join(str(tmp_path), TWIN_B), 'deleted')
    assert index.duplicates_stale() is True, 'the surviving twin is now unique'


def test_a_content_change_makes_them_stale(index, tmp_path):
    """apply_change treats 'changed' as a no-op because a row is derived from
    the filename. Duplicates are derived from the bytes, so this one matters.
    """
    loaded_with_twins(index, tmp_path)
    path = write(tmp_path, TWIN_B, 'no longer identical')
    index.apply_change(path, 'changed')
    assert index.duplicates_stale() is True


def test_an_attribute_change_leaves_them_alone(index, tmp_path):
    """A chmod or a touch does not alter a byte, so rescanning would be waste."""
    loaded_with_twins(index, tmp_path)
    index.apply_change(os.path.join(str(tmp_path), TWIN_A), 'attribute-changed')
    assert index.duplicates_stale() is False


def test_a_rename_keeps_the_pairing_without_rescanning(index, tmp_path):
    """A rename moves no bytes, so the answer is still known: remap the key
    rather than throwing away a scan that is still correct."""
    loaded_with_twins(index, tmp_path)
    renamed = '20240315-ES-HOU-BANK-INV-renamed-JOHNDOE.pdf'
    os.rename(os.path.join(str(tmp_path), TWIN_A),
              os.path.join(str(tmp_path), renamed))
    index.apply_change(os.path.join(str(tmp_path), TWIN_A), 'renamed',
                       os.path.join(str(tmp_path), renamed))

    assert index.duplicates_stale() is False, 'a rename does not change content'
    assert index.duplicates_of(renamed) == [TWIN_B]
    assert index.duplicates_of(TWIN_B) == [renamed]
    assert index.duplicates_of(TWIN_A) == []


def test_scanning_emits_so_the_view_can_refresh(index, tmp_path):
    write(tmp_path, TWIN_A, 'identical')
    write(tmp_path, TWIN_B, 'identical')
    index.reload()
    seen = []
    index.connect('duplicates-scanned', lambda *_a: seen.append(True))
    index.scan_duplicates()
    assert seen == [True]


def test_scanning_an_empty_repository_is_not_an_error(index):
    index.reload()
    index.scan_duplicates()
    assert index.duplicates_stale() is False
    assert index.duplicates_of('anything.pdf') == []


def test_a_worker_scan_emits_on_the_main_thread(index, tmp_path):
    """scan_duplicates runs in a worker, so its signal has to cross back.

    The workspace handler for this signal refilters the column view, and GTK may
    only be touched from the main loop. Emitting straight from the worker ran
    that refilter on the worker thread: two threads inside
    gtk_list_item_manager_model_items_changed_cb on the same list, and the
    process dumped core (24 Aug 2026, while filtering the workspace).
    """
    write(tmp_path, TWIN_A, 'identical')
    write(tmp_path, TWIN_B, 'identical')
    index.reload()

    emitted_on = []
    loop = GLib.MainLoop()

    def on_scanned(*_args):
        emitted_on.append(threading.current_thread())
        loop.quit()
        return False

    index.connect('duplicates-scanned', on_scanned)
    worker = threading.Thread(target=index.scan_duplicates, name='test-scan')
    worker.start()
    # Never hang the suite on a signal that does not arrive.
    guard = GLib.timeout_add_seconds(5, loop.quit)
    loop.run()
    GLib.source_remove(guard)
    worker.join(timeout=5)

    assert emitted_on == [threading.main_thread()], 'the signal crossed no thread boundary'


# ---------------------------------------------------------------------------
# field_used: the question asked before a configured value is deleted
# ---------------------------------------------------------------------------

def test_field_used_names_the_documents_holding_a_value(tmp_path, index):
    from MiAZ.backend.models import Country
    touch(tmp_path, VALID)
    touch(tmp_path, '20240316-ES-HOU-BANK-INV-second-JOHNDOE.pdf')
    index.reload()
    used, docs = index.field_used(Country, 'ES')
    assert used is True
    assert sorted(os.path.basename(doc) for doc in docs) == [
        VALID, '20240316-ES-HOU-BANK-INV-second-JOHNDOE.pdf']


def test_field_used_says_no_for_a_value_no_document_carries(tmp_path, index):
    from MiAZ.backend.models import Country
    touch(tmp_path, VALID)
    index.reload()
    assert index.field_used(Country, 'PT') == (False, [])


def test_field_used_indexes_first_when_it_has_not_yet(tmp_path, index):
    """A wrong 'nothing uses it' loses a value documents still reference, so
    an index that has never been loaded must answer by loading, not by
    reporting its empty state as an answer."""
    from MiAZ.backend.models import Country
    touch(tmp_path, VALID)
    used, docs = index.field_used(Country, 'ES')
    assert used is True
    assert len(docs) == 1


def test_field_used_reindexes_when_the_repository_changed(tmp_path, index):
    """The check MiAZUtil used to make with its own copy of this index: answer
    about the repository that is open, never about the last one."""
    from MiAZ.backend.models import Country
    touch(tmp_path, VALID)
    index.reload()

    other = tmp_path / 'other'
    other.mkdir()
    (other / '20240401-PT-HOU-BANK-INV-moved-JOHNDOE.pdf').write_text('x')
    index.app._repo.docs = str(other)

    assert index.field_used(Country, 'ES') == (False, [])
    used, _docs = index.field_used(Country, 'PT')
    assert used is True


def test_field_used_does_not_raise_on_a_model_it_does_not_index(tmp_path, index):
    """A plugin's own config is not one of the seven filename fields."""
    touch(tmp_path, VALID)
    index.reload()
    assert index.field_used(object(), 'anything') == (False, [])
