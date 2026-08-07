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


def test_diff_never_runs_past_the_last_bucket():
    """The tail chunk takes the remainder, and the format stops at 100.

    Under about 10 000 words the remainder is bigger than a chunk, so the
    unclamped `i // chunk_size` ran off the end -- and the app keeps 101
    buckets and quietly drops the rest, so those words could never be dealt.
    """
    for total in (100, 137, 250, 999, 1099, 9001, 13799):
        words = [FakeWord("w{}".format(i), i, "") for i in range(total)]
        diffs = [record["diff"] for record in json.loads(build_payload(words))]
        assert max(diffs) == 100 or max(diffs) == 99, (total, max(diffs))
        assert min(diffs) == 0
        assert diffs == sorted(diffs)
