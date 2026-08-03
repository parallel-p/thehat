# -*- coding: utf-8 -*-
"""CPython 2.7 semantics that the statistics pipeline depends on.

The rating maths in :mod:`app.stats` is order-sensitive: rating groups are
sorted by explanation time, and ties are broken by the order the words come out
of a dict. CPython 2.7 dicts are open-addressing tables iterated in *slot*
order; python3 dicts are iterated in insertion order. For the small non-negative
integer keys used here the two orders differ often enough to change ratings, so
the old table layout is emulated exactly rather than approximated.

Reference: CPython 2.7 ``Objects/dictobject.c`` (``lookdict``, ``insertdict``,
``dictresize``, ``PyDict_SetItem``, ``PyDict_DelItem``, ``PyDict_Clear``).
"""

import math

PERTURB_SHIFT = 5
MINSIZE = 8


class _Dummy:
    __slots__ = ()

    def __repr__(self):
        return "<dummy>"


DUMMY = _Dummy()


def py2_round(value):
    """``round()`` with python2 semantics: halves go away from zero.

    Python 3 rounds halves to even, and explanation times are computed as
    ``round(milliseconds / 1000.0)``, which lands exactly on .5 whenever the
    millisecond value ends in 500.
    """
    floor = math.floor(value)
    diff = value - floor
    if diff > 0.5:
        return int(floor) + 1
    if diff < 0.5:
        return int(floor)
    # exactly .5
    return int(floor) + 1 if value >= 0 else int(floor)


class Py2IntDict:
    """A dict with CPython 2.7 iteration order, for non-negative int keys.

    ``hash(n) == n`` for such keys in python2, which is what makes the slot
    layout reproducible without reimplementing python2's hashing.

    Set ``default_factory`` to get :class:`collections.defaultdict` behaviour
    (``d[missing]`` inserts and returns the default), which is what the original
    code used.
    """

    def __init__(self, default_factory=None):
        self.default_factory = default_factory
        self.clear()

    # -- internals ---------------------------------------------------------

    def clear(self):
        # PyDict_Clear always drops back to the 8-slot small table.
        self._size = MINSIZE
        self._slots = [None] * MINSIZE
        self._fill = 0  # active + dummy slots
        self._used = 0  # active slots

    def _lookup(self, key):
        """Return the slot index holding ``key``, or where it would be inserted."""
        mask = self._size - 1
        perturb = key
        i = key & mask
        slot = self._slots[i]
        if slot is None:
            return i
        if slot is not DUMMY and slot[0] == key:
            return i
        freeslot = i if slot is DUMMY else None
        while True:
            i = ((i << 2) + i + perturb + 1) & mask
            slot = self._slots[i]
            if slot is None:
                return i if freeslot is None else freeslot
            if slot is not DUMMY and slot[0] == key:
                return i
            if slot is DUMMY and freeslot is None:
                freeslot = i
            perturb >>= PERTURB_SHIFT

    def _insert_clean(self, key, value):
        """Insertion into a table known to contain neither ``key`` nor dummies."""
        mask = self._size - 1
        perturb = key
        i = key & mask
        while self._slots[i] is not None:
            i = ((i << 2) + i + perturb + 1) & mask
            perturb >>= PERTURB_SHIFT
        self._slots[i] = [key, value]
        self._fill += 1
        self._used += 1

    def _resize(self, minused):
        newsize = MINSIZE
        while newsize <= minused:
            newsize <<= 1
        old_slots = self._slots
        self._size = newsize
        self._slots = [None] * newsize
        self._fill = 0
        self._used = 0
        for slot in old_slots:
            if slot is not None and slot is not DUMMY:
                self._insert_clean(slot[0], slot[1])

    # -- mapping protocol --------------------------------------------------

    def __setitem__(self, key, value):
        i = self._lookup(key)
        slot = self._slots[i]
        if slot is not None and slot is not DUMMY:
            slot[1] = value
            return
        self._slots[i] = [key, value]
        self._used += 1
        if slot is None:
            self._fill += 1
        # PyDict_SetItem grows when the table is two-thirds full.
        if self._fill * 3 >= self._size * 2:
            self._resize(4 * self._used)

    def __getitem__(self, key):
        slot = self._slots[self._lookup(key)]
        if slot is None or slot is DUMMY:
            if self.default_factory is None:
                raise KeyError(key)
            value = self.default_factory()
            self[key] = value
            return value
        return slot[1]

    def get(self, key, default=None):
        slot = self._slots[self._lookup(key)]
        if slot is None or slot is DUMMY:
            return default
        return slot[1]

    def __contains__(self, key):
        slot = self._slots[self._lookup(key)]
        return slot is not None and slot is not DUMMY

    def __delitem__(self, key):
        i = self._lookup(key)
        slot = self._slots[i]
        if slot is None or slot is DUMMY:
            raise KeyError(key)
        self._slots[i] = DUMMY
        self._used -= 1

    _MISSING = object()

    def pop(self, key, default=_MISSING):
        i = self._lookup(key)
        slot = self._slots[i]
        if slot is None or slot is DUMMY:
            if default is self._MISSING:
                raise KeyError(key)
            return default
        self._slots[i] = DUMMY
        self._used -= 1
        return slot[1]

    def __len__(self):
        return self._used

    def __iter__(self):
        for slot in self._slots:
            if slot is not None and slot is not DUMMY:
                yield slot[0]

    def keys(self):
        return list(self)

    def values(self):
        return [self._slots[i][1] for i in self._active_slots()]

    def items(self):
        return [(self._slots[i][0], self._slots[i][1]) for i in self._active_slots()]

    def _active_slots(self):
        return [i for i, slot in enumerate(self._slots)
                if slot is not None and slot is not DUMMY]

    def __repr__(self):
        return "Py2IntDict({!r})".format(self.items())
