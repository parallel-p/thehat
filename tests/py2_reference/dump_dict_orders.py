# -*- coding: utf-8 -*-
"""Record real CPython 2.7 dict iteration orders, under python 2.7.

    ~/.pyenv/versions/2.7.18/bin/python tests/py2_reference/dump_dict_orders.py \\
        > tests/fixtures/py2_dict_orders.json

``tests/test_py2compat.py`` replays the same operation sequences through
:class:`app.py2compat.Py2IntDict` and asserts identical iteration order. This is
the ground truth for the emulation -- it is not derived from reading the CPython
source, it is measured.
"""

import json
import random
import sys


def run(operations):
    d = {}
    for op in operations:
        kind = op[0]
        if kind == 'set':
            d[op[1]] = op[2]
        elif kind == 'del':
            d.pop(op[1], None)
        elif kind == 'clear':
            d.clear()
    return list(d.keys())


def main():
    rng = random.Random(4242)
    cases = []

    # Ascending inserts across every resize boundary.
    for n in range(0, 130):
        cases.append([['set', i, i * 10] for i in range(n)])

    # Sparse keys: the interesting case, where key % size collides.
    for n in [5, 6, 10, 21, 22, 40, 86, 100]:
        for _ in range(6):
            keys = rng.sample(range(0, 400), n)
            cases.append([['set', k, k] for k in keys])

    # Inserts interleaved with deletions, which leave dummy slots behind.
    for _ in range(60):
        ops = []
        live = []
        for _ in range(rng.randint(5, 120)):
            if live and rng.random() < 0.25:
                key = rng.choice(live)
                live.remove(key)
                ops.append(['del', key])
            else:
                key = rng.randint(0, 300)
                if key not in live:
                    live.append(key)
                ops.append(['set', key, key])
        cases.append(ops)

    # clear() in the middle, as parse_log_v1 does every round.
    for _ in range(30):
        ops = []
        for _round in range(rng.randint(2, 8)):
            for _ in range(rng.randint(1, 12)):
                key = rng.randint(0, 200)
                ops.append(['set', key, key])
            ops.append(['clear'])
        for _ in range(rng.randint(1, 20)):
            ops.append(['set', rng.randint(0, 200), 1])
        cases.append(ops)

    out = [{'ops': ops, 'order': run(ops)} for ops in cases]
    json.dump(out, sys.stdout)
    sys.stderr.write('dumped {} cases from python {}\n'.format(
        len(out), sys.version.split()[0]))


if __name__ == '__main__':
    main()
