#!/usr/bin/python3

"""UI: the workspace. Checklist section 2."""

import os
import shutil
import time


def test_documents_are_listed(clean_view):
    """2.1: the repository's documents reach the view."""
    displayed = clean_view.displayed()
    assert len(displayed) == 3
    assert '20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf' in displayed


def test_labels_are_expanded_not_codes(clean_view):
    """2.1: the view shows descriptions, not the raw filename fields."""
    index = clean_view.service('index')
    item = index.document('20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf')
    assert item.country == 'ES'
    assert item.country_dsc == 'Spain'
    assert item.date_dsc and item.date_dsc != item.date


def test_search_narrows_the_list(clean_view):
    """2.8: typing in the search box filters as you type."""
    searchentry = clean_view.widget('searchentry')
    searchentry.set_text('mortgage')
    clean_view.pump(0.5)
    displayed = clean_view.displayed()
    assert len(displayed) == 1
    assert 'mortgage' in displayed[0]


def test_clearing_the_search_restores_the_list(clean_view):
    """2.9."""
    searchentry = clean_view.widget('searchentry')
    searchentry.set_text('mortgage')
    clean_view.pump(0.4)
    searchentry.set_text('')
    clean_view.pump(0.5)
    assert len(clean_view.displayed()) == 3


def test_search_is_case_insensitive(clean_view):
    """2.8."""
    searchentry = clean_view.widget('searchentry')
    searchentry.set_text('MORTGAGE')
    clean_view.pump(0.5)
    assert len(clean_view.displayed()) == 1


def test_selecting_rows_updates_the_header_buttons(clean_view):
    """2.4 and 6.1: one selection shows Rename, several show mass rename."""
    clean_view.select_documents('20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf')
    clean_view.pump(0.3)
    assert clean_view.widget('headerbar-button-rename').get_visible() is True
    assert clean_view.widget('headerbar-button-massrename').get_visible() is False

    clean_view.select_documents(
        '20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf',
        '20260505-ES-HOU-ACME-INV-electricity-JOHNDOE.pdf')
    clean_view.pump(0.3)
    assert clean_view.widget('headerbar-button-rename').get_visible() is False
    assert clean_view.widget('headerbar-button-massrename').get_visible() is True


def test_a_file_added_outside_the_app_appears(clean_view, sandbox):
    """2.10: the watcher notices a document arriving from a file manager."""
    name = '20260701-ES-FIN-BANKX-INV-watched-JOHNDOE.pdf'
    path = os.path.join(sandbox['Alpha'], name)
    with open(path, 'w', encoding='utf-8') as handler:
        handler.write('new')
    try:
        clean_view.wait_until(lambda: name in clean_view.displayed(),
                              message='the new document to appear')
    finally:
        os.unlink(path)
        clean_view.wait_until(lambda: name not in clean_view.displayed(),
                              message='the document to go again')


def test_a_file_copied_in_appears(clean_view, sandbox, tmp_path):
    """2.10, the way a file manager does it.

    A copy sets the timestamps after writing the bytes, so the last thing the
    monitor reports for the path is attribute-changed. The watcher collapses a
    burst to one event per path, so that is the only event the document ever
    produces: writing the file in place, which the test above does, ends in
    changes-done-hint instead and never exercised this.
    """
    name = '20260703-ES-FIN-BANKX-INV-copied-JOHNDOE.pdf'
    source = tmp_path / name
    source.write_text('copied')
    target = os.path.join(sandbox['Alpha'], name)
    shutil.copy2(str(source), target)
    try:
        clean_view.wait_until(lambda: name in clean_view.displayed(),
                              message='the copied document to appear')
    finally:
        os.unlink(target)
        clean_view.wait_until(lambda: name not in clean_view.displayed(),
                              message='the document to go again')


def test_a_copied_in_document_with_a_foreign_name_reaches_review(
        clean_view, sandbox, tmp_path):
    """2.10: what a scanner or a browser leaves in the repository.

    The name is not a MiAZ name, so the document belongs to the full scan,
    which renames it and puts it in Review.
    """
    source = tmp_path / 'bank statement.pdf'
    source.write_text('scanned')
    normalized = '-----BANK_STATEMENT-.pdf'
    target = os.path.join(sandbox['Alpha'], normalized)
    shutil.copy2(str(source), os.path.join(sandbox['Alpha'], 'bank statement.pdf'))
    toggle = clean_view.widget('workspace-togglebutton-pending-docs')
    try:
        clean_view.wait_until(lambda: os.path.exists(target),
                              message='the document to be renamed on disk')
        toggle.set_active(True)
        clean_view.wait_until(lambda: normalized in clean_view.displayed(),
                              message='the document to reach Review')
    finally:
        toggle.set_active(False)
        for name in ('bank statement.pdf', normalized):
            path = os.path.join(sandbox['Alpha'], name)
            if os.path.exists(path):
                os.unlink(path)
        clean_view.wait_until(lambda: normalized not in clean_view.displayed(),
                              message='the document to go again')


def test_a_file_deleted_outside_the_app_disappears(clean_view, sandbox):
    """2.11: and the count drops by exactly one."""
    name = '20260702-ES-FIN-BANKX-INV-temporary-JOHNDOE.pdf'
    path = os.path.join(sandbox['Alpha'], name)
    with open(path, 'w', encoding='utf-8') as handler:
        handler.write('new')
    clean_view.wait_until(lambda: name in clean_view.displayed(),
                          message='the document to appear')
    before = len(clean_view.displayed())

    os.unlink(path)
    clean_view.wait_until(lambda: name not in clean_view.displayed(),
                          message='the document to go')
    assert len(clean_view.displayed()) == before - 1


def test_a_search_that_finds_nothing_shows_the_empty_page(clean_view):
    """No documents on screen: no toolbar, the empty page and its buttons.

    It used to swap the whole workspace for a "No documents found" page with
    no buttons at all, so a repository with nothing in it had no way to add
    anything. Alpha holds a document waiting for review, so Review is offered
    too: with the toolbar hidden, the page is the only way to reach it.
    """
    clean_view.widget('searchentry').set_text('no-document-is-called-this')
    clean_view.wait_until(lambda: not clean_view.displayed(),
                          message='the list to empty')
    clean_view.pump(0.3)

    toolbar = clean_view.widget('workspace-toolbar')
    empty = clean_view.widget('workspace-empty')
    assert clean_view.widget('stack').get_visible_child_name() == 'workspace'
    assert not toolbar.get_mapped()
    assert empty.get_mapped()
    assert empty.status_page.get_title() == 'No documents found'
    assert empty.button_add.get_mapped()
    assert empty.button_review.get_mapped()

    clean_view.widget('searchentry').set_text('')
    clean_view.wait_until(lambda: len(clean_view.displayed()) == 3,
                          message='the list to come back')
    clean_view.pump(0.3)
    assert toolbar.get_mapped()
    assert not empty.get_mapped()


def test_the_first_paint_is_quick(miaz):
    """14.4: a filter pass must not take long enough to be felt."""
    started = time.monotonic()
    miaz.workspace.update()
    miaz.pump(0.5)
    assert time.monotonic() - started < 2.0
