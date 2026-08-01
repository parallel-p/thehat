# -*- coding: utf-8 -*-
"""Contract 7 against the Datastore emulator: the writes the golden trace stubs out."""

import datetime
import json

import pytest

from app import stats
from app.models import (DailyStatistics, GameLength, GamesForPlayerCount,
                        GameLog, GlobalDictionaryWord, REASON_CODES,
                        TotalStatistics, UnknownWord, WordLookup)


# --------------------------------------------------------------------------
# check_word
# --------------------------------------------------------------------------


def test_check_word_records_unknown_words(ndb_context):
    stats.check_word("кот")
    unknown = UnknownWord.get_by_id("кот")
    assert unknown is not None
    assert unknown.times_used == 1

    stats.check_word("кот")
    assert UnknownWord.get_by_id("кот").times_used == 2


def test_check_word_respects_the_ignored_flag(ndb_context):
    UnknownWord(id="кот", word="кот", times_used=5, ignored=True).put()
    stats.check_word("кот")
    assert UnknownWord.get_by_id("кот").times_used == 5


def test_check_word_ignores_known_words(ndb_context):
    GlobalDictionaryWord(id="кот", word="кот").put()
    stats.check_word("кот")
    assert UnknownWord.get_by_id("кот") is None


def test_known_word_lookup_follows_the_alias_table(ndb_context):
    GlobalDictionaryWord(id="кот", word="кот").put()
    WordLookup(id="коты", proper_word="кот").put()
    assert GlobalDictionaryWord.get("КоТы").word == "кот"
    assert GlobalDictionaryWord.get("такого-нет") is None


# --------------------------------------------------------------------------
# update_word
# --------------------------------------------------------------------------


class FakeRating:
    def __init__(self, mu, sigma):
        self.mu = mu
        self.sigma = sigma


class FakeKey:
    def urlsafe(self):
        return b"game-key-1"


def test_update_word_accumulates_counters(ndb_context):
    GlobalDictionaryWord(id="кот", word="кот", E=50.0, D=16.0).put()

    stats.update_word("кот", "guessed", 12, FakeRating(55.5, 9.25), FakeKey())
    word = GlobalDictionaryWord.get_by_id("кот")
    assert word.used_times == 1
    assert word.guessed_times == 1
    assert word.failed_times == 0
    assert word.total_explanation_time == 12
    assert word.E == 55.5
    assert word.D == 9.25
    assert word.used_games == ["game-key-1"]
    # 12 // 5 == bucket 2, so the list is padded out to length 3.
    assert word.counts_by_expl_time == [0, 0, 1]

    stats.update_word("кот", "failed", 3, FakeRating(40.0, 8.0), FakeKey())
    word = GlobalDictionaryWord.get_by_id("кот")
    assert word.used_times == 2
    assert word.failed_times == 1
    assert word.total_explanation_time == 15
    # Only 'guessed' outcomes land in the histogram.
    assert word.counts_by_expl_time == [0, 0, 1]
    assert word.used_games == ["game-key-1", "game-key-1"]


def test_update_word_is_a_noop_for_unknown_words(ndb_context):
    stats.update_word("нетуменя", "guessed", 5, FakeRating(1.0, 1.0), FakeKey())
    assert GlobalDictionaryWord.get_by_id("нетуменя") is None


def test_danger_keeps_python2_integer_division(ndb_context):
    """The legacy `failed/used` was floor division and is preserved as such."""
    GlobalDictionaryWord(id="w", word="w", used_times=10, failed_times=3).put()
    assert GlobalDictionaryWord.get_by_id("w").danger == 0
    GlobalDictionaryWord(id="w2", word="w2", used_times=2, failed_times=2).put()
    assert GlobalDictionaryWord.get_by_id("w2").danger == 1


# --------------------------------------------------------------------------
# aggregate statistics
# --------------------------------------------------------------------------


def test_update_daily_statistics(ndb_context):
    game_date = stats.get_date(1700023704)
    stats.update_daily_statistics(game_date, 20, 4, 1800)
    stats.update_daily_statistics(game_date, 15, 3, 1200)

    daily = DailyStatistics.get_by_id(str(game_date))
    assert daily.games == 2
    assert daily.words_used == 35
    assert daily.players_participated == 7
    assert daily.total_game_duration == 3000
    assert daily.date == datetime.datetime.fromtimestamp(game_date)


def test_get_date_truncates_to_a_whole_day():
    assert stats.get_date(1700023704) % 86400 == 0
    assert stats.get_date(1700023704) <= 1700023704


def test_update_statistics_by_player_count(ndb_context):
    stats.update_statistics_by_player_count(5)
    stats.update_statistics_by_player_count(5)
    stats.update_statistics_by_player_count(3)
    assert GamesForPlayerCount.get_by_id("5").games == 2
    assert GamesForPlayerCount.get_by_id("3").games == 1
    assert GamesForPlayerCount.get_by_id("5").player_count == 5


def test_update_total_statistics_buckets_by_hour_of_week(ndb_context):
    # 1700023704 is Tue 14 Nov 2023 21:28:24 UTC.
    game_time = 1700023704
    expected_bucket = game_time // 3600 % (24 * 7)
    stats.update_total_statistics(20, game_time)

    total = TotalStatistics.get()
    assert total.games == 1
    assert total.words_used == 20
    assert len(total.by_hour) == 24 * 7
    assert total.by_hour[expected_bucket] == 1
    assert sum(total.by_hour) == 1


def test_update_total_statistics_without_a_timestamp(ndb_context):
    stats.update_total_statistics(7, None)
    total = TotalStatistics.get()
    assert total.games == 1
    assert total.words_used == 7
    assert sum(total.by_hour) == 0


def test_total_statistics_default_is_not_shared_between_instances(ndb_context):
    """`by_hour` used to be a class-level mutable default -- a classic ndb trap."""
    first = TotalStatistics.get()
    first.by_hour[0] += 1
    second = TotalStatistics.get()
    assert second.by_hour[0] == 0


def test_update_game_len_prediction(ndb_context):
    stats.update_game_len_prediction(4, "game", 1000)
    stats.update_game_len_prediction(4, "game", 2000)
    entry = GameLength.get_by_id("game_4")
    assert entry.lens == [1000, 2000]
    assert entry.player_count == 4


# --------------------------------------------------------------------------
# end to end through the pipeline
# --------------------------------------------------------------------------


def v2_log(word_times, players=("a", "b")):
    attempts = []
    for index, (word, ms) in enumerate(word_times):
        attempts.append({"word": word, "from": players[index % len(players)],
                         "to": players[(index + 1) % len(players)],
                         "time": ms, "extra_time": 0, "outcome": "guessed"})
    return json.dumps({"version": "2.0", "start_timestamp": 1700000000000,
                       "end_timestamp": 1700001800000, "time_zone_offset": 0,
                       "attempts": attempts}, ensure_ascii=False)


def test_pipeline_end_to_end(ndb_context):
    for word in ["кот", "дом", "мост", "лес"]:
        GlobalDictionaryWord(id=word, word=word, E=50.0, D=16.0, lang="ru").put()
    from app.models import Dictionary
    Dictionary(id="ru").put()

    payload = v2_log([("кот", 8000), ("дом", 12000), ("мост", 5000), ("лес", 21000)])
    log = GameLog(json=payload)
    key = log.put()

    assert stats.add_game_to_statistic(key) == "ok"

    updated = {w.word: w for w in GlobalDictionaryWord.query().fetch()}
    assert all(w.used_times == 1 for w in updated.values())
    assert all(w.guessed_times == 1 for w in updated.values())
    # Ratings must have moved away from the seed value.
    assert any(abs(w.E - 50.0) > 1e-6 for w in updated.values())

    assert TotalStatistics.get().games == 1
    assert GameLog.get_by_id(key.id()).time is not None
    assert GameLog.get_by_id(key.id()).ignored is False


def test_pipeline_marks_too_few_words_as_ignored(ndb_context):
    payload = json.dumps({
        "setup": {"type": "hat", "meta": {"game.id": "g"},
                  "words": [{"word": "w{}".format(i)} for i in range(20)],
                  "players": ["a", "b"]},
        "events": [{"type": "start_game", "time": 1000}],
    })
    key = GameLog(json=payload, id="g").put()

    assert stats.add_game_to_statistic(key) == "ignored:suspect_too_little_words"
    log = GameLog.get_by_id("g")
    assert log.ignored is True
    assert log.reason == REASON_CODES["suspect_too_little_words"]


def test_pipeline_marks_freeplay_as_old_version(ndb_context):
    payload = json.dumps({"setup": {"type": "freeplay", "meta": {"game.id": "f"},
                                    "words": [], "players": []},
                          "events": []})
    key = GameLog(json=payload, id="f").put()
    assert stats.add_game_to_statistic(key) == "ignored:old_version"
    assert GameLog.get_by_id("f").reason == REASON_CODES["old_version"]


def test_pipeline_tolerates_a_missing_log(ndb_context):
    from google.cloud import ndb

    assert stats.add_game_to_statistic(ndb.Key(GameLog, "nope")) == "skipped:missing"


def test_internal_endpoint_requires_the_queue_header(client, ndb_context, monkeypatch):
    monkeypatch.setattr("app.internal.settings.ON_APPENGINE", True)
    response = client.post("/internal/add_game_to_statistic",
                           data={"game_key": "whatever"})
    assert response.status_code == 403


def test_internal_endpoint_runs_the_pipeline(client, ndb_context):
    from app.models import Dictionary
    Dictionary(id="ru").put()
    GlobalDictionaryWord(id="кот", word="кот", E=50.0, D=16.0, lang="ru").put()
    GlobalDictionaryWord(id="дом", word="дом", E=50.0, D=16.0, lang="ru").put()

    key = GameLog(json=v2_log([("кот", 8000), ("дом", 12000)])).put()
    response = client.post("/internal/add_game_to_statistic",
                           data={"game_key": key.urlsafe().decode()},
                           headers={"X-AppEngine-QueueName": "logs-processing"})
    assert response.status_code == 200
    assert GlobalDictionaryWord.get_by_id("кот").used_times == 1


@pytest.mark.parametrize("reason", sorted(REASON_CODES))
def test_every_ignore_reason_has_a_distinct_code(reason):
    codes = list(REASON_CODES.values())
    assert len(set(codes)) == len(codes)
    assert set(codes) == set(range(len(codes)))
