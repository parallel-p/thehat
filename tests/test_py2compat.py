# -*- coding: utf-8 -*-
"""Py2IntDict must reproduce measured CPython 2.7 dict behaviour."""

import json
import os

import pytest

from app.py2compat import Py2IntDict, py2_round

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
ORDERS = os.path.join(FIXTURES, "py2_dict_orders.json")


def replay(operations):
    d = Py2IntDict()
    for op in operations:
        kind = op[0]
        if kind == "set":
            d[op[1]] = op[2]
        elif kind == "del":
            d.pop(op[1], None)
        elif kind == "clear":
            d.clear()
    return list(d)


def test_iteration_order_matches_cpython27():
    if not os.path.exists(ORDERS):
        pytest.skip("run tests/py2_reference/dump_dict_orders.py under python 2.7")
    with open(ORDERS, encoding="utf-8") as handle:
        cases = json.load(handle)

    assert len(cases) > 200
    for index, case in enumerate(cases):
        assert replay(case["ops"]) == case["order"], "case {}".format(index)


def test_defaultdict_behaviour():
    d = Py2IntDict(lambda: 0)
    d[7] += 3
    d[7] += 4
    assert d[7] == 7
    assert 7 in d
    assert 8 not in d           # __contains__ must not insert
    assert len(d) == 1
    assert d[8] == 0            # __getitem__ must insert
    assert len(d) == 2


def test_pop_and_len():
    d = Py2IntDict(lambda: 0)
    for i in range(10):
        d[i] = i
    assert d.pop(4) == 4
    assert d.pop(4, None) is None
    assert 4 not in d
    assert len(d) == 9
    assert list(d) == [0, 1, 2, 3, 5, 6, 7, 8, 9]
    with pytest.raises(KeyError):
        d.pop(4)


def test_items_and_values_follow_iteration_order():
    d = Py2IntDict()
    for key in [40, 3, 17, 8]:
        d[key] = key * 2
    keys = list(d)
    assert [k for k, _ in d.items()] == keys
    assert d.values() == [d[k] for k in keys]


@pytest.mark.parametrize("value,expected", [
    (0.5, 1), (1.5, 2), (2.5, 3), (3.5, 4), (4.5, 5),
    (0.4, 0), (0.6, 1), (2.4999, 2), (2.5001, 3),
    (0.0, 0), (7.0, 7), (12.5, 13),
])
def test_py2_round_halves_go_away_from_zero(value, expected):
    assert py2_round(value) == expected
    if expected != round(value):
        # These are exactly the cases where python3's banker's rounding differs.
        assert value % 1 == 0.5


def test_py2_round_differs_from_builtin_on_even_halves():
    # Sanity: the fixture set must actually contain a divergence, otherwise the
    # helper is untested.
    divergent = [v for v in [0.5, 2.5, 4.5, 6.5] if py2_round(v) != round(v)]
    assert divergent == [0.5, 2.5, 4.5, 6.5]
