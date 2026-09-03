#!/usr/bin/python3

"""Where the MiAZExport2Dir plugin puts each exported document.

The `export` package lives under the plugin directory, which is not on the
default path, so the test inserts it the way the plugin does at runtime.
"""

import os
import sys

import pytest

PLUGIN_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'resources', 'plugins', 'MiAZExport2Dir')


@pytest.fixture(autouse=True)
def _plugin_path():
    if PLUGIN_DIR not in sys.path:
        sys.path.insert(0, PLUGIN_DIR)


FIELDS = ['20260904', 'ES', 'FIN', 'BANKX', 'INV', 'mortgage', 'JOHNDOE']
LABELS = ['', 'Spain', 'Finance', 'Bank X', 'Invoice', 'mortgage', 'John Doe']


# pattern validation

def test_every_documented_letter_is_valid():
    from export.layout import PATTERNS, invalid_keys
    assert invalid_keys(''.join(PATTERNS)) == []


def test_an_unknown_letter_is_reported():
    from export.layout import invalid_keys
    assert invalid_keys('CYxGz') == ['x', 'z']


def test_an_unknown_letter_is_reported_once():
    from export.layout import invalid_keys
    assert invalid_keys('xx') == ['x']


# directory_parts

def test_the_pattern_letters_become_directories_in_order():
    from export.layout import directory_parts
    assert directory_parts(FIELDS, 'CYmGP') == ['ES', '2026', '09', 'FIN', 'INV']


def test_the_day_is_two_digits():
    from export.layout import directory_parts
    assert directory_parts(['20260904'] + FIELDS[1:], 'Ymd') == ['2026', '09', '04']


def test_the_parties_have_their_own_letters():
    from export.layout import directory_parts
    assert directory_parts(FIELDS, 'BT') == ['BANKX', 'JOHNDOE']


def test_a_date_that_is_not_a_date_is_an_error():
    from export.layout import directory_parts
    fields = ['notadate'] + FIELDS[1:]
    with pytest.raises(ValueError):
        directory_parts(fields, 'Y')


def test_a_date_that_is_not_a_date_is_fine_when_the_pattern_ignores_it():
    from export.layout import directory_parts
    fields = ['notadate'] + FIELDS[1:]
    assert directory_parts(fields, 'CG') == ['ES', 'FIN']


def test_an_empty_field_becomes_the_placeholder():
    from export.layout import UNKNOWN, directory_parts
    fields = ['20260904', '', 'FIN', 'BANKX', 'INV', 'mortgage', 'JOHNDOE']
    assert directory_parts(fields, 'CG') == [UNKNOWN, 'FIN']


def test_a_separator_in_a_field_cannot_climb_out_of_the_target():
    from export.layout import directory_parts
    fields = ['20260904', '../etc', 'FIN', 'BANKX', 'INV', 'mortgage', 'JOHNDOE']
    parts = directory_parts(fields, 'C')
    assert os.sep not in parts[0]
    assert parts[0] != '..'


def test_labels_replace_the_keys_when_they_are_given():
    from export.layout import directory_parts
    assert directory_parts(FIELDS, 'CGP', LABELS) == ['Spain', 'Finance', 'Invoice']


def test_a_field_with_no_label_keeps_its_key():
    from export.layout import directory_parts
    labels = list(LABELS)
    labels[2] = ''
    assert directory_parts(FIELDS, 'CG', labels) == ['Spain', 'FIN']


def test_the_month_stays_a_number_even_with_labels():
    from export.layout import directory_parts
    assert directory_parts(FIELDS, 'Ym', LABELS) == ['2026', '09']


# readable_name

def test_the_readable_name_uses_the_descriptions_and_a_human_date():
    from export.layout import readable_name
    assert readable_name(FIELDS, 'pdf', LABELS) == (
        '2026-09-04 - Spain - Finance - Bank X - Invoice - mortgage - John Doe.pdf')


def test_the_readable_name_falls_back_to_the_keys():
    from export.layout import readable_name
    assert readable_name(FIELDS, 'pdf') == (
        '2026-09-04 - ES - FIN - BANKX - INV - mortgage - JOHNDOE.pdf')


def test_the_readable_name_skips_an_empty_field():
    from export.layout import readable_name
    fields = ['20260904', 'ES', '', 'BANKX', 'INV', 'mortgage', 'JOHNDOE']
    assert readable_name(fields, 'pdf') == (
        '2026-09-04 - ES - BANKX - INV - mortgage - JOHNDOE.pdf')


def test_the_readable_name_keeps_a_date_it_cannot_read():
    from export.layout import readable_name
    fields = ['notadate'] + FIELDS[1:]
    assert readable_name(fields, 'pdf').startswith('notadate - ES')


def test_the_readable_name_has_no_directory_separator():
    from export.layout import readable_name
    fields = ['20260904', 'ES', 'FIN', 'BANKX', 'INV', 'a/b', 'JOHNDOE']
    assert os.sep not in readable_name(fields, 'pdf')


def test_the_readable_name_works_without_an_extension():
    from export.layout import readable_name
    assert readable_name(FIELDS, '') == (
        '2026-09-04 - ES - FIN - BANKX - INV - mortgage - JOHNDOE')


# unique_target

def test_a_free_name_is_left_alone():
    from export.layout import unique_target
    assert unique_target('/tmp/a.pdf', set()) == '/tmp/a.pdf'


def test_a_taken_name_gets_a_counter_before_the_extension():
    from export.layout import unique_target
    assert unique_target('/tmp/a.pdf', {'/tmp/a.pdf'}) == '/tmp/a (2).pdf'


def test_the_counter_climbs_until_the_name_is_free():
    from export.layout import unique_target
    taken = {'/tmp/a.pdf', '/tmp/a (2).pdf', '/tmp/a (3).pdf'}
    assert unique_target('/tmp/a.pdf', taken) == '/tmp/a (4).pdf'


# export_documents: what reaches the target, and what is reported back

def document(doc_id=None, fields=None, labels=None, extension='pdf'):
    fields = list(FIELDS if fields is None else fields)
    if doc_id is None:
        doc_id = '-'.join(fields) + f'.{extension}'
    return (doc_id, fields, labels, extension)


def copier(copied, refuse=()):
    """A stand-in for the repository copy: records what it was asked to do."""
    def copy(source, target):
        if os.path.basename(source) in refuse:
            return False
        copied.append((source, target))
        return True
    return copy


def test_without_a_pattern_everything_lands_in_the_target():
    from export.runner import export_documents
    done = []
    count, failures = export_documents([document(), document(fields=[
        '20260905', 'ES', 'FIN', 'BANKX', 'INV', 'rent', 'JOHNDOE'])],
        '/out', '/repo', copier(done))
    assert (count, failures) == (2, [])
    assert [target for _source, target in done] == [
        '/out/20260904-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf',
        '/out/20260905-ES-FIN-BANKX-INV-rent-JOHNDOE.pdf']


def test_the_source_is_read_from_the_repository(tmp_path):
    from export.runner import export_documents
    done = []
    export_documents([document(doc_id='a.pdf')], str(tmp_path), '/repo/docs',
                     copier(done))
    assert done[0][0] == '/repo/docs/a.pdf'


def test_the_pattern_creates_the_directories(tmp_path):
    from export.runner import export_documents
    done = []
    count, failures = export_documents([document()], str(tmp_path), '/repo',
                                       copier(done), pattern='CYm')
    assert (count, failures) == (1, [])
    assert (tmp_path / 'ES' / '2026' / '09').is_dir()
    assert done[0][1] == str(tmp_path / 'ES' / '2026' / '09' /
                             '20260904-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf')


def test_readable_names_rename_the_copy_and_the_directories(tmp_path):
    from export.runner import export_documents
    done = []
    export_documents([document(labels=LABELS)], str(tmp_path), '/repo',
                     copier(done), pattern='C', readable=True)
    assert done[0][1] == str(tmp_path / 'Spain' /
                             '2026-09-04 - Spain - Finance - Bank X - '
                             'Invoice - mortgage - John Doe.pdf')


def test_the_directories_keep_the_keys_when_the_names_are_not_readable(tmp_path):
    from export.runner import export_documents
    done = []
    export_documents([document(labels=LABELS)], str(tmp_path), '/repo',
                     copier(done), pattern='C')
    assert (tmp_path / 'ES').is_dir()


def test_a_name_that_is_not_in_miaz_format_is_reported(tmp_path):
    from export.runner import export_documents
    done = []
    broken = ('holiday.pdf', ['holiday'], None, 'pdf')
    count, failures = export_documents([broken, document()], str(tmp_path),
                                       '/repo', copier(done), pattern='Y')
    assert count == 1
    assert failures[0][0] == 'holiday.pdf'
    assert len(done) == 1


def test_a_copy_that_did_not_happen_is_reported():
    from export.runner import export_documents
    done = []
    doc = document(doc_id='gone.pdf')
    count, failures = export_documents([doc], '/out', '/repo',
                                       copier(done, refuse={'gone.pdf'}))
    assert count == 0
    assert failures[0][0] == 'gone.pdf'


def test_two_documents_with_the_same_readable_name_both_survive(tmp_path):
    from export.runner import export_documents
    done = []
    first = document(doc_id='one.pdf', labels=LABELS)
    second = document(doc_id='two.pdf', labels=LABELS)
    count, failures = export_documents([first, second], str(tmp_path), '/repo',
                                       copier(done), readable=True)
    assert (count, failures) == (2, [])
    assert done[0][1] != done[1][1]
    assert done[1][1].endswith(' (2).pdf')


def test_every_document_is_reported_while_it_is_copied():
    from export.runner import export_documents
    seen = []
    documents = [document(doc_id='a.pdf'), document(doc_id='b.pdf')]
    export_documents(documents, '/out', '/repo', copier([]),
                     report=lambda text, fraction: seen.append((text, fraction)))
    assert seen == [('a.pdf', 0.5), ('b.pdf', 1.0)]
