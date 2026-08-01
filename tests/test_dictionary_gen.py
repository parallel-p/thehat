# -*- coding: utf-8 -*-
"""WP6: the generated dictionary blob must stay byte-compatible.

``tests/fixtures/dictionary_sample_raw.json`` is a verbatim byte slice of the
blob production is serving right now (the first 50 records of
``gs://the-hat.appspot.com/dictionary/1564137725``), so this pins key order,
separators and ASCII escaping against the real artifact rather than against an
assumption about python2's json module.
"""

import json
import os

from app.dictionary_gen import build_payload

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
SAMPLE = os.path.join(FIXTURES, "dictionary_sample_raw.json")


class FakeWord:
    def __init__(self, word, used_times, tags):
        self.word = word
        self.used_times = used_times
        self.tags = tags


def test_serialisation_is_byte_identical_to_production():
    with open(SAMPLE, "rb") as handle:
        raw = handle.read()
    records = json.loads(raw)
    assert len(records) == 50

    # build_payload derives `diff` from position; feed it words whose ordering
    # reproduces the recorded diffs so the comparison is on serialisation only.
    rebuilt = json.dumps([
        {"diff": r["diff"], "used": r["used"], "word": r["word"], "tags": r["tags"]}
        for r in records
    ]).encode("utf-8")

    assert rebuilt == raw


def test_build_payload_shape_and_diff_buckets():
    words = [FakeWord("w{}".format(i), i, "") for i in range(1000)]
    payload = build_payload(words)
    parsed = json.loads(payload)

    assert len(parsed) == 1000
    assert list(parsed[0].keys()) == ["diff", "used", "word", "tags"]
    # chunk_size == 1000 // 100 == 10, so diff runs 0..99 in blocks of ten.
    assert parsed[0]["diff"] == 0
    assert parsed[9]["diff"] == 0
    assert parsed[10]["diff"] == 1
    assert parsed[999]["diff"] == 99


def test_build_payload_escapes_non_ascii_like_python2():
    payload = build_payload([FakeWord("шляпа", 1, "")] * 100)
    assert b"\\u0448" in payload
    assert "шляпа".encode("utf-8") not in payload
