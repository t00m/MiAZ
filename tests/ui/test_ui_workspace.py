#!/usr/bin/python3

"""UI: the workspace. Checklist section 2."""

import os
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


def test_the_first_paint_is_quick(miaz):
    """14.4: a filter pass must not take long enough to be felt."""
    started = time.monotonic()
    miaz.workspace.update()
    miaz.pump(0.5)
    assert time.monotonic() - started < 2.0
