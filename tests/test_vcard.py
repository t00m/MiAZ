#!/usr/bin/python3

"""What the vCard reader accepts.

The `contacts` package lives under the plugin directory, which is not on the
default path, so the test inserts it the way the plugin does at runtime.
"""

import os
import sys

import pytest

PLUGIN_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'resources', 'plugins', 'MiAZContacts')


@pytest.fixture(autouse=True)
def _plugin_path():
    if PLUGIN_DIR not in sys.path:
        sys.path.insert(0, PLUGIN_DIR)


def card(*lines):
    body = '\r\n'.join(('BEGIN:VCARD', 'VERSION:4.0') + lines + ('END:VCARD',))
    return body + '\r\n'


def test_a_card_yields_its_properties():
    from contacts import vcard
    cards = vcard.parse(card('FN:John Doe', 'EMAIL:john@example.com'))
    assert len(cards) == 1
    assert cards[0].get('FN').text() == 'John Doe'
    assert cards[0].get('EMAIL').text() == 'john@example.com'


def test_two_cards_in_one_file():
    from contacts import vcard
    cards = vcard.parse(card('FN:One') + card('FN:Two'))
    assert [one.get('FN').text() for one in cards] == ['One', 'Two']


def test_folded_lines_are_joined():
    from contacts import vcard
    text = card('NOTE:This note is long enough to be fol\r\n ded once')
    assert vcard.parse(text)[0].get('NOTE').text() == (
        'This note is long enough to be folded once')


def test_lines_folded_with_a_tab_are_joined():
    from contacts import vcard
    text = card('NOTE:first\r\n\tsecond')
    assert vcard.parse(text)[0].get('NOTE').text() == 'firstsecond'


def test_lf_only_input_is_accepted():
    from contacts import vcard
    text = 'BEGIN:VCARD\nVERSION:4.0\nFN:John Doe\nEND:VCARD\n'
    assert vcard.parse(text)[0].get('FN').text() == 'John Doe'


def test_escapes_are_undone():
    from contacts import vcard
    text = card(r'NOTE:one\, two\; three\nfour\\five')
    assert vcard.parse(text)[0].get('NOTE').text() == (
        'one, two; three\nfour\\five')


def test_structured_names_split_into_components():
    from contacts import vcard
    text = card('N:Doe;John;Peter;Dr.;Jr.')
    assert vcard.parse(text)[0].get('N').components() == [
        ['Doe'], ['John'], ['Peter'], ['Dr.'], ['Jr.']]


def test_a_component_can_hold_several_values():
    from contacts import vcard
    text = card('N:Doe;John;Peter,Paul;;')
    assert vcard.parse(text)[0].get('N').components()[2] == ['Peter', 'Paul']


def test_a_separator_inside_a_value_is_not_a_separator():
    from contacts import vcard
    text = card(r'ADR:;;Main St 1\, floor 2;Berlin;;10115;DE')
    parts = vcard.parse(text)[0].get('ADR').components()
    assert parts[2] == ['Main St 1, floor 2']
    assert parts[3] == ['Berlin']


def test_parameters_are_read():
    from contacts import vcard
    text = card('TEL;TYPE=work,voice;PREF=1:+49 30 123456')
    phone = vcard.parse(text)[0].get('TEL')
    assert phone.types() == ['work', 'voice']
    assert phone.is_preferred()
    assert phone.text() == '+49 30 123456'


def test_a_colon_inside_a_quoted_parameter_does_not_split_the_line():
    from contacts import vcard
    text = card('TEL;TYPE="work:main":+49 30 123456')
    phone = vcard.parse(text)[0].get('TEL')
    assert phone.text() == '+49 30 123456'
    assert phone.params['TYPE'] == ['work:main']


def test_vcard_21_bare_parameters_are_read_as_types():
    from contacts import vcard
    text = ('BEGIN:VCARD\r\nVERSION:2.1\r\nFN:John Doe\r\n'
            'TEL;HOME;VOICE:+49 30 123456\r\nEND:VCARD\r\n')
    parsed = vcard.parse(text)[0]
    assert parsed.version() == '2.1'
    assert parsed.get('TEL').types() == ['home', 'voice']


def test_quoted_printable_values_are_decoded():
    from contacts import vcard
    text = ('BEGIN:VCARD\r\nVERSION:2.1\r\n'
            'FN;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:Tom=C3=A1s\r\n'
            'END:VCARD\r\n')
    assert vcard.parse(text)[0].get('FN').text() == 'Tomás'


def test_a_quoted_printable_soft_break_joins_the_next_line():
    from contacts import vcard
    text = ('BEGIN:VCARD\r\nVERSION:2.1\r\n'
            'NOTE;ENCODING=QUOTED-PRINTABLE:one=\r\ntwo\r\n'
            'END:VCARD\r\n')
    assert vcard.parse(text)[0].get('NOTE').text() == 'onetwo'


def test_property_groups_are_kept():
    from contacts import vcard
    text = card('item1.X-MIAZ-IBAN:DE02120300000000202051',
                'item1.X-ABLabel:Salary')
    parsed = vcard.parse(text)[0]
    assert parsed.get('X-MIAZ-IBAN').group == 'item1'
    assert sorted(prop.name for prop in parsed.groups()['item1']) == [
        'X-ABLABEL', 'X-MIAZ-IBAN']


def test_all_returns_every_property_of_one_name():
    from contacts import vcard
    text = card('EMAIL:one@example.com', 'EMAIL:two@example.com')
    assert [prop.text() for prop in vcard.parse(text)[0].all('EMAIL')] == [
        'one@example.com', 'two@example.com']


def test_text_that_is_not_a_card_yields_nothing():
    from contacts import vcard
    assert vcard.parse('this is not a vcard') == []


def test_from_text_escapes_what_it_is_given():
    from contacts import vcard
    prop = vcard.Property.from_text('NOTE', 'one, two; three\nfour')
    assert prop.value == r'one\, two\; three\nfour'
    assert prop.text() == 'one, two; three\nfour'


def test_from_components_builds_a_structured_value():
    from contacts import vcard
    prop = vcard.Property.from_components(
        'N', ['Doe', 'John', ['Peter', 'Paul'], '', ''])
    assert prop.value == 'Doe;John;Peter,Paul;;'


def test_a_written_card_has_the_shape_of_a_card():
    from contacts import vcard
    text = vcard.serialize([vcard.Card([vcard.Property.from_text('FN', 'John Doe')])])
    assert text.startswith('BEGIN:VCARD\r\nVERSION:4.0\r\n')
    assert text.endswith('END:VCARD\r\n')
    assert 'FN:John Doe\r\n' in text


def test_the_writer_always_says_version_four():
    from contacts import vcard
    cards = vcard.parse('BEGIN:VCARD\r\nVERSION:3.0\r\nFN:John\r\nEND:VCARD\r\n')
    written = vcard.serialize(cards)
    assert 'VERSION:4.0' in written
    assert 'VERSION:3.0' not in written


def test_long_lines_are_folded_at_75_octets():
    from contacts import vcard
    prop = vcard.Property.from_text('NOTE', 'x' * 200)
    for line in vcard.format_line(prop).split('\r\n'):
        assert len(line.encode('utf-8')) <= 75


def test_folding_never_splits_a_character():
    from contacts import vcard
    prop = vcard.Property.from_text('NOTE', 'á' * 100)
    for line in vcard.format_line(prop).split('\r\n'):
        assert len(line.encode('utf-8')) <= 75
        line.encode('utf-8').decode('utf-8')


def test_a_folded_line_read_back_is_the_same_value():
    from contacts import vcard
    value = 'á' * 100
    text = vcard.serialize([vcard.Card([vcard.Property.from_text('NOTE', value)])])
    assert vcard.parse(text)[0].get('NOTE').text() == value


def test_parameters_are_written_back():
    from contacts import vcard
    prop = vcard.Property.from_text(
        'TEL', '+49 30 123456', params={'TYPE': ['work', 'voice'], 'PREF': ['1']})
    assert vcard.format_line(prop).startswith('TEL;PREF=1;TYPE=work,voice:')


def test_a_parameter_value_with_a_separator_is_quoted():
    from contacts import vcard
    prop = vcard.Property.from_text('TEL', '+49', params={'TYPE': ['work:main']})
    assert 'TYPE="work:main"' in vcard.format_line(prop)


def test_a_group_is_written_in_front_of_the_name():
    from contacts import vcard
    prop = vcard.Property.from_text('X-ABLabel', 'Salary', group='item1')
    assert vcard.format_line(prop).startswith('item1.X-ABLABEL:')


def test_an_unknown_property_survives_a_round_trip():
    from contacts import vcard
    original = ('BEGIN:VCARD\r\nVERSION:4.0\r\nFN:John Doe\r\n'
                'BDAY:19800101\r\nX-WHATEVER;TYPE=odd:kept\r\nEND:VCARD\r\n')
    again = vcard.parse(vcard.serialize(vcard.parse(original)))[0]
    assert again.get('BDAY').text() == '19800101'
    assert again.get('X-WHATEVER').text() == 'kept'
    assert again.get('X-WHATEVER').types() == ['odd']


def test_several_cards_are_written_one_after_another():
    from contacts import vcard
    cards = [vcard.Card([vcard.Property.from_text('FN', 'One')]),
             vcard.Card([vcard.Property.from_text('FN', 'Two')])]
    text = vcard.serialize(cards)
    assert text.count('BEGIN:VCARD') == 2
    assert [one.get('FN').text() for one in vcard.parse(text)] == ['One', 'Two']
