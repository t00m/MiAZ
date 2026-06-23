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
