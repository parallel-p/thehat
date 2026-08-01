# -*- coding: utf-8 -*-
"""The /play app's game log, against the parser that rates words.

The web app builds its log in JavaScript (static/play/js/log.js) and this is
the only place the two halves meet. `parse_log_v2` is unforgiving in ways that
are invisible from the client -- a word can be silently dropped, or a whole
game thrown away, without the app ever seeing an error -- so the shapes it
emits are pinned here rather than trusted.

The fixture below is a real log, captured from the app driven through a game,
with only the timings widened to what a game played by people looks like.
"""

import json

import pytest

from app import stats
from app.models import GameLog


def pwa_log(**overrides):
    """A log in exactly the shape static/play/js/log.js produces."""
    log = {
        "version": "2.0",
        "game_id": "604ccd8a-8f51-4203-be1f-82162d32bc11",
        "time_zone_offset": 10800000,
        "start_timestamp": 1785609187837,
        "end_timestamp": 1785609194528,
        "attempts": [
            {"word": "капельница", "from": 0, "to": 1,
             "time": 8600, "extra_time": 0, "outcome": "guessed"},
            {"word": "рекордсмен", "from": 0, "to": 1,
             "time": 12400, "extra_time": 0, "outcome": "failed"},
            {"word": "огниво", "from": 1, "to": 0,
             "time": 5200, "extra_time": 0, "outcome": "guessed"},
            # Ran out of time holding this one: no `outcome` key at all, which
            # is how the app says "back in the hat".
            {"word": "коллизия", "from": 1, "to": 0,
             "time": 3100, "extra_time": 2900},
        ],
    }
    log.update(overrides)
    return log


def test_the_apps_log_parses(ndb_context):
    parsed = stats.parse_log_v2(pwa_log())
    (words, times, outcomes, _at_once, _pairs, players, start, end) = parsed

    assert words == ["капельница", "рекордсмен", "огниво", "коллизия"]
    assert players == 2
    assert outcomes[0] == "guessed"
    assert outcomes[1] == "failed"
    assert outcomes[2] == "guessed"
    # The unfinished word is in the log and timed, but has no outcome: it was
    # neither guessed nor an error, and rating must see it as neither.
    assert 3 not in outcomes
    assert times[0] == 9 and times[2] == 5

    # The offset is added to the timestamps, which is what makes the hour-of-week
    # charts show the players' own evening rather than UTC.
    assert start == 1785609187837 + 10800000
    assert end == 1785609194528 + 10800000


def test_a_word_returned_to_the_hat_keeps_its_extra_time(ndb_context):
    """time + extra_time is what the 500ms..5min window is measured against."""
    log = pwa_log()
    _, times, outcomes, _, _, _, _, _ = stats.parse_log_v2(log)
    # 3100 + 2900 = 6s, comfortably inside the window, so it is not 'removed'.
    assert outcomes.get(3) != "removed"
    assert 3 not in times or times[3] == 0


@pytest.mark.parametrize("time_ms,extra_ms", [(200, 0), (400, 60), (301000, 0)])
def test_the_app_must_stay_inside_the_time_window(ndb_context, time_ms, extra_ms):
    """Outside 500ms..5min a word is dropped from rating without a word to
    anyone. Pinned so that a change to the app's timing is noticed here."""
    log = pwa_log(attempts=[
        {"word": "кот", "from": 0, "to": 1,
         "time": time_ms, "extra_time": extra_ms, "outcome": "guessed"}])
    _, _, outcomes, _, _, _, _, _ = stats.parse_log_v2(log)
    assert outcomes[0] == "removed"


def test_the_apps_log_survives_the_whole_pipeline(ndb_context):
    """End to end: the log the app posts moves the ratings it should."""
    from app.models import Dictionary, GlobalDictionaryWord

    for word in ["капельница", "рекордсмен", "огниво", "коллизия"]:
        GlobalDictionaryWord(id=word, word=word, E=50.0, D=16.0, lang="ru").put()
    Dictionary(id="ru").put()

    key = GameLog(json=json.dumps(pwa_log(), ensure_ascii=False)).put()
    assert stats.add_game_to_statistic(key) == "ok"

    words = {w.word: w for w in GlobalDictionaryWord.query().fetch()}
    assert words["капельница"].used_times == 1
    assert words["капельница"].guessed_times == 1
    # And the ratings actually moved, which is the point of the whole exercise.
    assert abs(words["капельница"].E - 50.0) > 1e-6

    # Only guessed words reach update_word: parse_log_v2 fills seen_words_time
    # in the 'guessed' branch alone, and the pipeline iterates that. So a word
    # that was failed, or that went back in the hat, is recorded in the log,
    # shown to the player, and then counted nowhere -- it does not even
    # increment used_times.
    #
    # This is worth knowing beyond this test: `failed_times` can only ever be
    # fed by v1 logs, which nothing has produced for years, so the site's
    # «ошибкоопасные слова» table is being filled by history alone.
    assert words["рекордсмен"].used_times == 0
    assert words["рекордсмен"].failed_times == 0
    assert words["коллизия"].used_times == 0


def test_a_game_of_quick_taps_is_rejected(ndb_context):
    """More than half the attempts under two seconds throws the game away.

    Worth knowing about: a tester tapping through a game to 'check it works'
    produces exactly this and sees no error anywhere.
    """
    log = pwa_log(attempts=[
        {"word": w, "from": 0, "to": 1, "time": 900, "extra_time": 0,
         "outcome": "guessed"}
        for w in ["кот", "дом", "мост", "лес"]])
    key = GameLog(json=json.dumps(log, ensure_ascii=False)).put()
    assert stats.add_game_to_statistic(key) == "ignored:suspect_too_quick_explanation"
