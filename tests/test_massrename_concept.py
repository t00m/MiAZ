import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), '..',
    'data', 'resources', 'plugins', 'MiAZMassRename'))

import concept_ops


def test_parse_positions_single():
    assert concept_ops.parse_positions('2', 5) == [1]


def test_parse_positions_range():
    assert concept_ops.parse_positions('2-3', 5) == [1, 2]


def test_parse_positions_open_ended():
    assert concept_ops.parse_positions('2-', 4) == [1, 2, 3]


def test_parse_positions_comma_list():
    assert concept_ops.parse_positions('1,3', 5) == [0, 2]


def test_parse_positions_out_of_range_dropped():
    assert concept_ops.parse_positions('2-99', 3) == [1, 2]


def test_parse_positions_invalid_ignored():
    assert concept_ops.parse_positions('x,2', 5) == [1]


def test_parse_positions_empty():
    assert concept_ops.parse_positions('', 5) == []


def test_keep_tokens_range():
    concept = '12_salary_slip_202508_00017381_20250827'
    assert concept_ops.keep_tokens(concept, '2-3') == 'salary_slip'


def test_keep_tokens_single():
    assert concept_ops.keep_tokens('a_b_c', '2') == 'b'


def test_keep_tokens_out_of_range_returns_empty():
    assert concept_ops.keep_tokens('a_b', '5') == ''


def test_remove_tokens_drops_positions():
    concept = '12_salary_slip_202508_00017381_20250827'
    # Drop the leading sequence number (1) and the trailing id+date (5-6).
    assert concept_ops.remove_tokens(concept, '1,5-6') == 'salary_slip_202508'


def test_remove_tokens_custom_separator():
    assert concept_ops.remove_tokens('a-b-c', '2', sep='-') == 'a-c'


def test_add_prefix():
    assert concept_ops.add_prefix('202508', 'PAYSLIP') == 'PAYSLIP_202508'


def test_add_prefix_empty_text_noop():
    assert concept_ops.add_prefix('202508', '') == '202508'


def test_add_suffix():
    assert concept_ops.add_suffix('salary', 'final') == 'salary_final'


def test_find_replace():
    assert concept_ops.find_replace('salary_slip', 'slip', 'doc') == 'salary_doc'


def test_find_replace_delete():
    assert concept_ops.find_replace('a_b_a', 'a', '') == '_b_'


def test_change_case():
    assert concept_ops.change_case('Salary_Slip', 'lower') == 'salary_slip'
    assert concept_ops.change_case('salary', 'upper') == 'SALARY'


def test_set_value():
    assert concept_ops.set_value('whatever', 'fixed') == 'fixed'


def test_apply_dispatch_keep():
    params = {'positions': '2-3', 'sep': '_'}
    assert concept_ops.apply('keep', '12_salary_slip_202508', params) == 'salary_slip'


def test_apply_unknown_op_returns_concept():
    assert concept_ops.apply('nope', 'abc', {}) == 'abc'
