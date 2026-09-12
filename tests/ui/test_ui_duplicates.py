#!/usr/bin/python3

"""UI: marking documents whose bytes match another one.

The scan reads files, so it runs in a worker and only on entering review mode.
Every document in the sandbox is written with the same content, which makes
them all duplicates of each other: convenient here, since what is under test is
the wiring from index to column to tooltip, not the hashing itself.
"""

import os

from gi.repository import Gtk

REVIEW_BUTTON = 'workspace-togglebutton-pending-docs'


def walk(widget):
    child = widget.get_first_child()
    while child is not None:
        yield child
        yield from walk(child)
        child = child.get_next_sibling()


def enter_review(driver):
    driver.widget(REVIEW_BUTTON).set_active(True)
    index = driver.service('index')
    driver.wait_until(lambda: not index.duplicates_stale(),
                      message='the duplicate scan')
    driver.pump(0.4)
    return index


def leave_review(driver):
    driver.widget(REVIEW_BUTTON).set_active(False)
    driver.pump(0.3)


def test_nothing_is_scanned_until_review_mode(clean_view):
    """A user who never opens review mode pays nothing for this."""
    assert clean_view.service('index').duplicates_stale() is True


def test_the_column_is_hidden_when_nothing_has_been_scanned(clean_view):
    """An empty column for everyone would be a permanent cost for a feature
    used occasionally."""
    assert clean_view.widget('workspace-view').column_duplicate.get_visible() is False


def test_review_mode_scans_and_finds_the_twins(clean_view):
    index = enter_review(clean_view)
    try:
        assert index.duplicates_stale() is False
        twins = index.duplicates_of('20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf')
        assert twins, 'no duplicate found for a document that has three'
        assert '20260505-ES-HOU-ACME-INV-electricity-JOHNDOE.pdf' in twins
    finally:
        leave_review(clean_view)


def test_the_column_appears_once_there_is_something_in_it(clean_view):
    enter_review(clean_view)
    try:
        column = clean_view.widget('workspace-view').column_duplicate
        assert column.get_visible() is True
    finally:
        leave_review(clean_view)


def test_a_marked_row_says_what_it_duplicates(clean_view):
    """The icon alone is not actionable: which copy to discard depends on
    whether the twin is already filed."""
    enter_review(clean_view)
    try:
        view = clean_view.widget('workspace-view')
        tooltips = [w.get_tooltip_text() for w in walk(view)
                    if isinstance(w, Gtk.Image) and w.get_tooltip_text()]
        marked = [t for t in tooltips if 'Same content as' in t]
        assert marked, 'no row carries a duplicate tooltip'
        assert any('.pdf' in t for t in marked), 'the twin is not named'
        assert any('already filed' in t or 'also pending' in t for t in marked), \
            'the tooltip does not say whether the twin is filed'
    finally:
        leave_review(clean_view)


def test_one_entry_into_review_mode_scans_once(clean_view):
    """The guard is duplicates_stale: a second trigger while the map is still
    good must not read every file again.

    Note what this does not claim. Toggling review mode off and on again does
    rescan, because the toggle reloads the index and a reload invalidates the
    map. That is the design: recompute rather than trust a map that may have
    gone stale. The scan is backgrounded, so the cost is a delay before the
    marks appear, not a frozen window.
    """
    index = enter_review(clean_view)
    try:
        calls = []
        real = index.scan_duplicates
        index.scan_duplicates = lambda: (calls.append(True), real())[1]
        try:
            workspace = clean_view.widget('workspace')
            workspace._scan_duplicates()
            workspace._scan_duplicates()
            clean_view.pump(0.4)
            assert calls == [], 'rescanned while the map was still valid'
        finally:
            index.scan_duplicates = real
    finally:
        leave_review(clean_view)


# ---------------------------------------------------------------------------
# Sorting the column
# ---------------------------------------------------------------------------

UNIQUE = '20240101-DE-ADM-CITY-NTF-permit-JOHNDOE.pdf'

# Review mode shows pending documents only, and the sandbox holds one, so the
# ordering is checked on the sort keys of every document rather than on rows.
ALL_DOCS = (
    '20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf',
    '20260505-ES-HOU-ACME-INV-electricity-JOHNDOE.pdf',
    '20240101-DE-ADM-CITY-NTF-permit-JOHNDOE.pdf',
    '20260401-ES-FIN-STRANGER-INV-unknown-JOHNDOE.pdf',
)


def with_one_unique_document(driver):
    """Give one document content of its own, so not everything is a duplicate.

    Every document in the sandbox is written with the same bytes, which makes
    the whole set one group and leaves nothing to sort against.
    """
    repo = driver.service('repo')
    path = os.path.join(repo.docs, UNIQUE)
    original = open(path, 'rb').read()
    open(path, 'wb').write(b'content belonging to nothing else')
    return path, original


def test_the_column_can_be_sorted(clean_view):
    assert clean_view.widget('workspace-view').column_duplicate.get_sorter() is not None


def sort_keys(driver, names):
    """The sort key the column would use for each named document."""
    view = driver.widget('workspace-view')
    index = driver.service('index')
    return {name: view._duplicate_sort_key(index.document(name)) for name in names}


def test_a_document_with_no_twin_sorts_after_every_one_that_has_one(clean_view):
    """Ascending has to bring the documents worth acting on to the top.

    The ordering is checked on the keys rather than on the view: review mode
    shows pending documents only, and the sandbox holds exactly one of those,
    so no arrangement of rows could show it.
    """
    path, original = with_one_unique_document(clean_view)
    try:
        index = enter_review(clean_view)
        keys = sort_keys(clean_view, [n for n in ALL_DOCS])
        assert not index.duplicates_of(UNIQUE), 'the unique document has a twin'
        for name, key in keys.items():
            if name == UNIQUE:
                assert key[0] == '\uffff', key
            else:
                assert key[0] != '\uffff', f'{name} sorted as if it had no twin'
                assert key < keys[UNIQUE], f'{name} sorts after the unique one'
    finally:
        open(path, 'wb').write(original)
        leave_review(clean_view)


def test_every_member_of_a_group_shares_one_key(clean_view):
    """This is what puts the copies next to each other. Two copies of one
    document are only comparable when they are adjacent."""
    path, original = with_one_unique_document(clean_view)
    try:
        index = enter_review(clean_view)
        twinned = [n for n in ALL_DOCS if index.duplicates_of(n)]
        assert len(twinned) >= 2, twinned
        keys = sort_keys(clean_view, twinned)
        groups = {key[0] for key in keys.values()}
        assert len(groups) == 1, f'one group split across keys {groups}'
    finally:
        open(path, 'wb').write(original)
        leave_review(clean_view)


def test_the_key_orders_within_a_group_by_name(clean_view):
    """Same group, so the second half of the key decides: a stable order the
    user can predict, rather than whatever the store happened to hold."""
    path, original = with_one_unique_document(clean_view)
    try:
        index = enter_review(clean_view)
        twinned = sorted(n for n in ALL_DOCS if index.duplicates_of(n))
        keys = sort_keys(clean_view, twinned)
        assert [k[1] for k in (keys[n] for n in twinned)] == twinned
    finally:
        open(path, 'wb').write(original)
        leave_review(clean_view)


def test_sorting_by_the_column_does_not_break_the_view(clean_view):
    """End to end: the sorter is real and the view survives using it."""
    path, original = with_one_unique_document(clean_view)
    try:
        enter_review(clean_view)
        view = clean_view.widget('workspace-view')
        for direction in (Gtk.SortType.ASCENDING, Gtk.SortType.DESCENDING):
            view.cv.sort_by_column(view.column_duplicate, direction)
            clean_view.pump(0.3)
            assert clean_view.displayed(), 'sorting emptied the view'
    finally:
        open(path, 'wb').write(original)
        leave_review(clean_view)


# ---------------------------------------------------------------------------
# Showing a group of copies without going through review mode
# ---------------------------------------------------------------------------

def sorted_ids(driver):
    """The document ids in the order the view is showing them."""
    view = driver.widget('workspace-view')
    model = view.get_model_filter()
    return [model.get_item(position).id for position in range(len(model))]


def test_show_duplicates_scans_and_reveals_the_column(clean_view):
    """The Doctor's Show puts a set of copies on screen, and nothing on that
    screen said which was a copy of which: the map is only scanned on entering
    review mode, and the column is only revealed by that scan.
    """
    workspace = clean_view.workspace
    view = clean_view.widget('workspace-view')
    index = clean_view.service('index')
    index._invalidate_duplicates()
    view.column_duplicate.set_visible(False)

    workspace.show_duplicates()
    clean_view.wait_until(lambda: not index.duplicates_stale(),
                          message='the duplicate scan')
    clean_view.pump(0.5)
    assert view.column_duplicate.get_visible() is True


def test_show_duplicates_puts_the_copies_next_to_each_other(clean_view):
    """Adjacency is the answer to "which of these is a copy of which".

    The sandbox documents all share their content, so one group holds them
    all: what is asserted is that the view is sorted by the copy column, not
    that any particular pair ended up together.
    """
    workspace = clean_view.workspace
    view = clean_view.widget('workspace-view')

    workspace.show_duplicates()
    clean_view.wait_until(lambda: not clean_view.service('index').duplicates_stale(),
                          message='the duplicate scan')
    clean_view.pump(0.5)

    shown = sorted_ids(clean_view)
    expected = sorted(shown, key=lambda name: view._duplicate_sort_key(
        clean_view.service('index').document(name)))
    assert shown == expected, 'the view is not in copy order'


def test_show_duplicates_does_not_rescan_what_is_already_known(clean_view):
    """The scan reads every file that shares a size with another one."""
    index = clean_view.service('index')
    workspace = clean_view.workspace
    workspace.show_duplicates()
    clean_view.wait_until(lambda: not index.duplicates_stale(),
                          message='the first scan')
    clean_view.pump(0.4)

    scans = []
    original = index.scan_duplicates
    index.scan_duplicates = lambda *args: scans.append(True) or original(*args)
    try:
        workspace.show_duplicates()
        clean_view.pump(1.0)
        assert scans == [], 'a fresh map was scanned again'
    finally:
        index.scan_duplicates = original
