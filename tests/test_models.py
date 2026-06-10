#!/usr/bin/python3

"""
Tests for MiAZ.backend.models — runs without a display (GObject only, no GTK/Adw).
"""

import gi
gi.require_version('GLib', '2.0')

import pytest
from MiAZ.backend.models import MiAZModel, MiAZItem


# ---------------------------------------------------------------------------
# MiAZModel tests
# ---------------------------------------------------------------------------

def test_model_id():
    obj = MiAZModel(id='test-doc', title='Test Document')
    assert obj.id == 'test-doc'


def test_model_title():
    obj = MiAZModel(id='test-doc', title='Test Document')
    assert obj.title == 'Test Document'


def test_model_empty_strings():
    obj = MiAZModel(id='', title='')
    assert obj.id == ''
    assert obj.title == ''


# ---------------------------------------------------------------------------
# MiAZItem tests
# ---------------------------------------------------------------------------

def test_item_basic_fields():
    item = MiAZItem(
        id='FAKE-XX-GRP-SND-PRP-concept-RCV',
        date='20010101',
        title='Fake document title',
        active=True,
        valid=True,
    )
    assert item.id == 'FAKE-XX-GRP-SND-PRP-concept-RCV'
    assert item.title == 'Fake document title'
    assert item.active is True
    assert item.valid is True


def test_item_defaults():
    item = MiAZItem(id='fake-id', title='')
    assert item.active is False
    assert item.valid is False
    assert item.extension == ''
    assert item.date == ''


def test_item_extension_stored():
    item = MiAZItem(id='fake-id', title='t', extension='pdf')
    assert item.extension == 'pdf'


def test_item_sentby_sentto():
    item = MiAZItem(
        id='fake-id',
        title='',
        sentby_id='FAKE_SENDER',
        sentto_id='FAKE_RECIPIENT',
    )
    assert item.sentby_id == 'FAKE_SENDER'
    assert item.sentto_id == 'FAKE_RECIPIENT'


def test_item_search_text_contains_id():
    item = MiAZItem(id='SEARCH-KEY-ID', title='some title')
    assert 'SEARCH-KEY-ID' in item.search_text


def test_item_search_text_upper_is_upper():
    item = MiAZItem(id='lower-id', title='lower title')
    assert item.search_text_upper == item.search_text.upper()


# ---------------------------------------------------------------------------
# Parametrized: MiAZModel id/title combinations
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("item_id,item_title", [
    ('fake-001', 'Alpha document'),
    ('fake-002', 'Beta document'),
    ('fake-003', ''),
    ('', 'Gamma document'),
])
def test_model_parametrize_id_title(item_id, item_title):
    obj = MiAZModel(id=item_id, title=item_title)
    assert obj.id == item_id
    assert obj.title == item_title
