#!/usr/bin/python3

"""
Tests for the pure concept-field transforms in the mass-rename service
(MiAZ.frontend.desktop.services.massrename).

These functions are module-level and side-effect free. The module imports GTK
and Adw, so the test sets the gi versions first (the app does the same in
miaz.py). Importing the module does not create widgets or need a display.

This restores the coverage that was dropped when MiAZMassRename moved from a
plugin (with a standalone concept_ops module) to a core service. The dispatcher
was renamed from apply() to apply_concept_op() in that move.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from MiAZ.frontend.desktop.services import massrename as m


# parse_positions: 1-based spec to sorted 0-based indices, out-of-range dropped

def test_parse_positions_single():
    assert m.parse_positions('2', 5) == [1]


def test_parse_positions_range():
    assert m.parse_positions('2-3', 5) == [1, 2]


def test_parse_positions_open_ended():
    assert m.parse_positions('2-', 4) == [1, 2, 3]


def test_parse_positions_open_start():
    # A leading hyphen means "from the first token".
    assert m.parse_positions('-3', 5) == [0, 1, 2]


def test_parse_positions_comma_list():
    assert m.parse_positions('1,3', 5) == [0, 2]


def test_parse_positions_out_of_range_dropped():
    assert m.parse_positions('2-99', 3) == [1, 2]


def test_parse_positions_invalid_ignored():
    assert m.parse_positions('x,2', 5) == [1]


def test_parse_positions_empty():
    assert m.parse_positions('', 5) == []


def test_parse_positions_none():
    assert m.parse_positions(None, 5) == []


def test_parse_positions_reversed_range_empty():
    # start > end yields an empty range, so nothing is selected.
    assert m.parse_positions('3-1', 5) == []


def test_parse_positions_deduplicates():
    assert m.parse_positions('2,2,2', 5) == [1]


# keep_tokens / remove_tokens

def test_keep_tokens_range():
    concept = '12_salary_slip_202508_00017381_20250827'
    assert m.keep_tokens(concept, '2-3') == 'salary_slip'


def test_keep_tokens_single():
    assert m.keep_tokens('a_b_c', '2') == 'b'


def test_keep_tokens_out_of_range_returns_empty():
    assert m.keep_tokens('a_b', '5') == ''


def test_keep_tokens_preserves_file_order_not_spec_order():
    # parse_positions sorts indices, so an out-of-order spec keeps file order.
    assert m.keep_tokens('a_b_c', '3,1') == 'a_c'


def test_remove_tokens_drops_positions():
    concept = '12_salary_slip_202508_00017381_20250827'
    # Drop the leading sequence number (1) and the trailing id+date (5-6).
    assert m.remove_tokens(concept, '1,5-6') == 'salary_slip_202508'


def test_remove_tokens_custom_separator():
    assert m.remove_tokens('a-b-c', '2', sep='-') == 'a-c'


def test_remove_tokens_none_dropped_returns_concept():
    assert m.remove_tokens('a_b_c', '') == 'a_b_c'


# add_prefix / add_suffix

def test_add_prefix():
    assert m.add_prefix('202508', 'PAYSLIP') == 'PAYSLIP_202508'


def test_add_prefix_empty_text_noop():
    assert m.add_prefix('202508', '') == '202508'


def test_add_prefix_empty_concept_returns_text():
    assert m.add_prefix('', 'PAYSLIP') == 'PAYSLIP'


def test_add_prefix_custom_separator():
    assert m.add_prefix('202508', 'PAYSLIP', sep='-') == 'PAYSLIP-202508'


def test_add_suffix():
    assert m.add_suffix('salary', 'final') == 'salary_final'


def test_add_suffix_empty_text_noop():
    assert m.add_suffix('salary', '') == 'salary'


def test_add_suffix_empty_concept_returns_text():
    assert m.add_suffix('', 'final') == 'final'


# find_replace

def test_find_replace():
    assert m.find_replace('salary_slip', 'slip', 'doc') == 'salary_doc'


def test_find_replace_delete():
    assert m.find_replace('a_b_a', 'a', '') == '_b_'


def test_find_replace_empty_find_noop():
    assert m.find_replace('salary_slip', '', 'doc') == 'salary_slip'


# change_case

def test_change_case_lower():
    assert m.change_case('Salary_Slip', 'lower') == 'salary_slip'


def test_change_case_upper():
    assert m.change_case('salary', 'upper') == 'SALARY'


def test_change_case_title():
    assert m.change_case('salary_slip', 'title') == 'Salary_Slip'


def test_change_case_unknown_mode_noop():
    assert m.change_case('Salary_Slip', 'sentence') == 'Salary_Slip'


# set_value

def test_set_value_replaces_everything():
    assert m.set_value('whatever_was_here', 'fixed') == 'fixed'


# apply_concept_op dispatcher

def test_apply_keep():
    params = {'positions': '2-3', 'sep': '_'}
    assert m.apply_concept_op('keep', '12_salary_slip_202508', params) == 'salary_slip'


def test_apply_remove():
    params = {'positions': '1'}
    assert m.apply_concept_op('remove', 'a_b_c', params) == 'b_c'


def test_apply_prefix():
    assert m.apply_concept_op('prefix', '202508', {'text': 'INV'}) == 'INV_202508'


def test_apply_suffix():
    assert m.apply_concept_op('suffix', 'salary', {'text': 'final'}) == 'salary_final'


def test_apply_replace():
    params = {'find': 'slip', 'replace': 'doc'}
    assert m.apply_concept_op('replace', 'salary_slip', params) == 'salary_doc'


def test_apply_case():
    assert m.apply_concept_op('case', 'salary', {'mode': 'upper'}) == 'SALARY'


def test_apply_set():
    assert m.apply_concept_op('set', 'whatever', {'value': 'fixed'}) == 'fixed'


def test_apply_uses_default_separator_when_blank():
    # An empty 'sep' falls back to '_'.
    params = {'positions': '2', 'sep': ''}
    assert m.apply_concept_op('keep', 'a_b_c', params) == 'b'


def test_apply_unknown_op_returns_concept():
    assert m.apply_concept_op('nope', 'abc', {}) == 'abc'
