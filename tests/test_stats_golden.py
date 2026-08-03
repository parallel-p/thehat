# -*- coding: utf-8 -*-
"""WP3 golden test: the python3 pipeline must match the python27 one exactly.

``tests/fixtures/stats_golden*.jsonl`` was produced by running the *original*
``legacy/handlers/statistics/calculation.py`` under python 2.7 with the vendored
trueskill (see ``tests/py2_reference/run_reference.py`` and the ``golden`` target
in the Makefile). This test replays the same logs through :mod:`app.stats` with
the same Datastore stubs and asserts the traces are identical: same words, same
order, same outcomes, same explanation times, and TrueSkill mu/sigma equal to
within 1e-9.

If this fails, the port has diverged from production behaviour. Do not "fix" the
golden file -- fix the port.
"""

import json
import os

import pytest

from app import stats

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
TOLERANCE = 1e-9

# (logs, golden traces, word rating snapshot)
GOLDEN_SETS = [
    ("synthetic_logs.jsonl", "stats_golden_synthetic.jsonl", "word_ratings.json"),
    ("prod_logs.jsonl", "stats_golden_prod.jsonl", "word_ratings_prod.json"),
]


class FakeWord:
    def __init__(self, word, E, D, lang):
        self.word = word
        self.E = E
        self.D = D
        self.lang = lang


class FakeLog:
    def __init__(self, entity_id, payload):
        self.entity_id = entity_id
        self.json = payload
        self.time = None
        self.ignored = False
        self.reason = None

    def put(self):
        return None

    def set_reason(self, name):
        from app.models import REASON_CODES

        self.reason = REASON_CODES[name]


class FakeKey:
    def __init__(self, entity):
        self._entity = entity

    def kind(self):
        return "GameLog"

    def id(self):
        return self._entity.entity_id

    def get(self):
        return self._entity

    def urlsafe(self):
        return b"fake-urlsafe"


def load_words(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as handle:
        raw = json.load(handle)
    return {word.lower(): FakeWord(word, spec["E"], spec["D"], spec.get("lang", "ru"))
            for word, spec in raw.items()}


def load_jsonl(name):
    path = os.path.join(FIXTURES, name)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def run_port(log_entry, words_by_key, monkeypatch):
    """Run app.stats with the same stubs the python2 reference used."""
    trace = []

    monkeypatch.setattr(stats, "check_word", lambda word: None)
    monkeypatch.setattr(stats, "get_langs", lambda: ["ru"])

    class StubGlobalDictionaryWord:
        @staticmethod
        def get(word):
            return words_by_key.get(word.lower())

    monkeypatch.setattr(stats, "GlobalDictionaryWord", StubGlobalDictionaryWord)
    monkeypatch.setattr(stats, "update_daily_statistics",
                        lambda game_date, word_count, players_count, duration:
                        trace.append(["daily", game_date, word_count, players_count, duration]))
    monkeypatch.setattr(stats, "update_statistics_by_player_count",
                        lambda player_count: trace.append(["by_player_count", player_count]))
    monkeypatch.setattr(stats, "update_total_statistics",
                        lambda word_count, game_time=None:
                        trace.append(["total", word_count, game_time]))
    monkeypatch.setattr(stats, "update_game_len_prediction",
                        lambda player_count, game_type, game_len:
                        trace.append(["game_len", player_count, game_type, game_len]))
    monkeypatch.setattr(stats, "update_word",
                        lambda word, outcome, explanation_time, rating, game_key:
                        trace.append(["word", word, outcome, explanation_time,
                                      repr(rating.mu) if rating else None,
                                      repr(rating.sigma) if rating else None]))

    fake_log = FakeLog(log_entry["id"], log_entry["json"])
    result = stats.add_game_to_statistic(FakeKey(fake_log))
    return {
        "id": log_entry["id"],
        "outcome": "aborted" if result.startswith("ignored") else "ok",
        "ignored": fake_log.ignored,
        "time": fake_log.time.isoformat() if fake_log.time else None,
        "trace": trace,
    }


def assert_trace_equal(actual, expected, game_id):
    assert actual["outcome"] == expected["outcome"], game_id
    assert actual["ignored"] == expected["ignored"], game_id
    assert actual["time"] == expected["time"], game_id
    assert len(actual["trace"]) == len(expected["trace"]), (
        "{}: {} entries vs {}".format(game_id, len(actual["trace"]),
                                      len(expected["trace"])))

    for index, (got, want) in enumerate(zip(actual["trace"], expected["trace"])):
        where = "{} entry {}".format(game_id, index)
        assert got[0] == want[0], where
        if got[0] == "word":
            assert got[1:4] == want[1:4], "{}: {} vs {}".format(where, got, want)
            for got_value, want_value in zip(got[4:6], want[4:6]):
                if want_value is None:
                    assert got_value is None, where
                else:
                    assert abs(float(got_value) - float(want_value)) < TOLERANCE, (
                        "{}: {} vs {}".format(where, got_value, want_value))
        else:
            assert got == want, "{}: {} vs {}".format(where, got, want)


@pytest.mark.parametrize("logs_name,golden_name,words_name", GOLDEN_SETS)
def test_matches_python27_reference(logs_name, golden_name, words_name, monkeypatch):
    logs = load_jsonl(logs_name)
    golden = load_jsonl(golden_name)
    if logs is None or golden is None:
        pytest.skip("fixtures {}/{} not generated".format(logs_name, golden_name))

    words_by_key = load_words(words_name)
    expected_by_id = {entry["id"]: entry for entry in golden}
    assert len(expected_by_id) == len(golden), "duplicate ids in golden file"

    compared = 0
    for log_entry in logs:
        expected = expected_by_id[log_entry["id"]]
        actual = run_port(log_entry, words_by_key, monkeypatch)
        assert_trace_equal(actual, expected, log_entry["id"])
        compared += 1
    assert compared == len(golden)


def test_golden_traces_actually_rate_words():
    """Guard against the golden file silently degenerating into empty traces."""
    golden = load_jsonl("stats_golden_synthetic.jsonl")
    assert golden, "synthetic golden fixture missing"
    word_entries = [row for entry in golden for row in entry["trace"]
                    if row[0] == "word"]
    rated = [row for row in word_entries if row[4] is not None]
    assert len(word_entries) > 500
    assert len(rated) > 400
