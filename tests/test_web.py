# -*- coding: utf-8 -*-
"""Contract 8: the web pages that survived the migration."""

import datetime

from app.models import (DailyStatistics, GamesForPlayerCount,
                        GlobalDictionaryWord, TotalStatistics)


def test_index_serves_the_landing_page(client, ndb_context):
    response = client.get("/")
    assert response.status_code == 200
    assert "ЛКШ.Шляпа" in response.text
    assert response.headers["content-type"].startswith("text/html")


def test_status_endpoints(client, ndb_context):
    assert client.get("/_status").json() == {"status": "ok"}
    assert client.get("/_ah/warmup").status_code == 200


def test_index_is_byte_identical_to_the_static_landing_handler(client, ndb_context):
    """`/` is served by the app, `/landing` by an app.yaml static handler."""
    import os

    from app.web import LANDING_PAGE

    with open(LANDING_PAGE, "rb") as handle:
        assert client.get("/").content == handle.read()
    assert os.path.basename(LANDING_PAGE) == "landing.html"


def test_word_statistics_lists_hardest_and_easiest(client, ndb_context):
    for index in range(12):
        GlobalDictionaryWord(id="w{}".format(index), word="w{}".format(index),
                             E=float(index), D=5.0, used_times=index).put()
    response = client.get("/statistics/word_statistics")
    assert response.status_code == 200
    assert "Самые сложные" in response.text
    assert "w11" in response.text


def test_word_statistics_for_a_single_word(client, ndb_context):
    GlobalDictionaryWord(id="кот", word="кот", E=61.25, D=4.0, used_times=10,
                         guessed_times=8, failed_times=1,
                         total_explanation_time=80,
                         counts_by_expl_time=[0, 3, 5]).put()
    response = client.get("/statistics/word_statistics", params={"word": "КОТ"})
    assert response.status_code == 200

    # The difficulty is the number the page leads with.
    assert "61.2" in response.text or "61.3" in response.text
    assert 'class="hero-figure"' in response.text
    # ...and the uncertainty is shown as +-2D, not the raw sigma.
    assert "8.0" in response.text

    # Outcome bars are proportional to used_times: 8/10 guessed, 1/10 failed.
    assert "width: 80.0%" in response.text
    assert "width: 10.0%" in response.text
    # The explanation-time histogram is scaled to its own peak.
    assert "height: 100.0%" in response.text
    # Every chart also has a table view.
    assert "Показать таблицей" in response.text


def test_word_statistics_survives_a_word_with_no_attempts(client, ndb_context):
    """A freshly added word has used_times == 0; nothing may divide by it."""
    GlobalDictionaryWord(id="новое", word="новое", E=50.0, D=16.6).put()
    response = client.get("/statistics/word_statistics", params={"word": "новое"})
    assert response.status_code == 200
    assert "новое" in response.text


def test_word_statistics_for_a_missing_word(client, ndb_context):
    response = client.get("/statistics/word_statistics", params={"word": "нетслова"})
    assert response.status_code == 200
    assert "нет слова" in response.text


def test_total_statistics(client, ndb_context):
    total = TotalStatistics.get()
    total.games = 42
    total.words_used = 1234
    total.by_hour[5] = 7
    total.put()
    GamesForPlayerCount(id="4", player_count=4, games=9).put()
    DailyStatistics(id="1700006400",
                    date=datetime.datetime(2023, 11, 15),
                    games=3, words_used=60, players_participated=12,
                    total_game_duration=5400).put()

    response = client.get("/statistics/total_statistics")
    assert response.status_code == 200
    assert "42" in response.text
    assert "1234" in response.text
    assert "2023-11-15" in response.text
    # by_hour[5] is the only non-zero hour, so it is the peak column.
    assert "height: 100.0%" in response.text
    # A single player-count row is also its own peak.
    assert "width: 100.0%" in response.text


def test_total_statistics_on_an_empty_database(client, ndb_context):
    """No games yet: every chart divides by a peak of zero if unguarded."""
    response = client.get("/statistics/total_statistics")
    assert response.status_code == 200
    assert "Пока нет данных по дням" in response.text


def test_statistics_pages_are_not_indexable(client, ndb_context):
    response = client.get("/statistics/total_statistics")
    assert 'name="robots"' in response.text
