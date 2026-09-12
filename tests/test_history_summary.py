#!/usr/bin/python3

"""How a step is described to the user.

Git words are banned here, and so is file content: the dialog says which files
a step touched, never what is inside them.
"""

import os
import sys
import time
import datetime

import pytest

PLUGIN_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'resources', 'plugins', 'MiAZHistory')

BANNED = ('commit', 'git', 'revert', 'checkout', 'HEAD', 'branch')


@pytest.fixture(autouse=True)
def _plugin_path():
    if PLUGIN_DIR not in sys.path:
        sys.path.insert(0, PLUGIN_DIR)


def at(year, month, day, hour, minute):
    return datetime.datetime(year, month, day, hour, minute)


def stamp(moment):
    return int(moment.timestamp())


# subject: what a step is called when it is recorded

def test_one_renamed_document_is_named_in_the_singular():
    from history.summary import subject
    assert subject({'renamed': 1}) == 'Renamed 1 document'


def test_several_renamed_documents_are_named_in_the_plural():
    from history.summary import subject
    assert subject({'renamed': 3}) == 'Renamed 3 documents'


def test_a_step_that_did_two_things_names_both():
    from history.summary import subject
    assert subject({'renamed': 1, 'added': 2}) == 'Added 2 documents, renamed 1 document'


def test_a_configuration_change_is_named_as_one():
    from history.summary import subject
    assert subject({'config': 1}) == 'Changed settings'


def test_a_change_nobody_claimed_says_where_it_came_from():
    """Only the watcher spoke, so MiAZ did not make this change."""
    from history.summary import subject
    assert subject({}) == 'Changed outside MiAZ'


# when: the timestamp, in words

def test_today_is_written_as_today():
    from history.summary import when
    now = at(2026, 9, 7, 19, 2)
    assert when(stamp(at(2026, 9, 7, 10, 12)), now) == 'Today at 10:12'


def test_yesterday_is_written_as_yesterday():
    from history.summary import when
    now = at(2026, 9, 7, 19, 2)
    assert when(stamp(at(2026, 9, 6, 18, 7)), now) == 'Yesterday at 18:07'


def test_an_older_step_carries_its_date_and_its_time():
    from history.summary import when
    now = at(2026, 9, 7, 19, 2)
    written = when(stamp(at(2026, 9, 3, 9, 24)), now)
    assert '09:24' in written
    assert '3' in written


# config_label: a configuration file, in the user's words

def test_a_vocabulary_file_is_named_by_its_vocabulary():
    from history.summary import config_label
    assert config_label('.conf/senders-used.json') == 'Senders'
    assert config_label('.conf/countries-available.json') == 'Countries'


def test_the_plugin_list_is_named_plugins():
    from history.summary import config_label
    assert config_label('.conf/plugins-used.json') == 'Plugins'


def test_a_plugin_settings_file_is_named_after_its_plugin():
    from history.summary import config_label
    assert config_label('.conf/plugins/MiAZDoctor/conf/Plugin-MiAZDoctor.json') == \
        'MiAZDoctor settings'


def test_a_document_is_not_a_configuration_file():
    from history.summary import config_label
    assert config_label('20260101-ES-FIN-BANKX-INV-rent-JOHNDOE.pdf') is None


# sections: what the dialog lists

def test_each_kind_of_change_gets_its_own_section():
    from history.summary import sections
    listed = sections([('A', 'a.pdf', ''), ('D', 'b.pdf', ''), ('M', 'c.pdf', '')])
    assert [title for title, _lines in listed] == ['Added', 'Changed', 'Deleted']


def test_a_rename_shows_both_names():
    from history.summary import sections
    listed = sections([('R', 'old.pdf', 'new.pdf')])
    assert listed == [('Renamed', ['old.pdf -> new.pdf'])]


def test_configuration_changes_are_gathered_under_one_heading():
    from history.summary import sections
    listed = sections([('A', 'a.pdf', ''), ('M', '.conf/senders-used.json', '')])
    assert listed == [('Added', ['a.pdf']), ('Configuration', ['Senders'])]


def test_a_long_section_is_cut_off_and_says_how_many_are_left():
    from history.summary import sections
    changes = [('A', f'{number}.pdf', '') for number in range(20)]
    _title, lines = sections(changes)[0]
    assert len(lines) == 13
    assert lines[-1] == 'and 8 more'


# body and headline

def test_the_body_starts_with_the_timestamp():
    from history.summary import body
    now = at(2026, 9, 7, 19, 2)
    written = body([('A', 'a.pdf', '')], stamp(at(2026, 9, 7, 10, 12)), now)
    assert written.splitlines()[0] == 'Today at 10:12'


def test_the_body_never_says_git():
    from history.summary import body
    written = body([('A', 'a.pdf', ''), ('R', 'b.pdf', 'c.pdf'),
                    ('M', '.conf/senders-used.json', '')], int(time.time()))
    for word in BANNED:
        assert word not in written.lower()


def test_the_headline_is_one_line_for_a_tooltip():
    from history.summary import headline
    assert headline([('R', 'a.pdf', 'b.pdf')]) == 'Renamed 1 document'
    assert headline([('A', 'a.pdf', ''), ('A', 'b.pdf', '')]) == 'Added 2 documents'
