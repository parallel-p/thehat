# -*- coding: utf-8 -*-
"""Contract 8: the web pages that survived the migration."""

import datetime

from app.models import (DailyStatistics, GamesForPlayerCount,
                        GlobalDictionaryWord, TotalStatistics)


def test_index_serves_the_landing_page(client, ndb_context):
    response = client.get("/")
    assert response.status_code == 200
    assert "Объясняйте" in response.text
    assert response.headers["content-type"].startswith("text/html")


def test_status_endpoints(client, ndb_context):
    assert client.get("/_status").json() == {"status": "ok"}
    assert client.get("/_ah/warmup").status_code == 200


def test_index_states_what_the_server_has_collected(client, ndb_context):
    """The landing page's argument for itself is two live numbers.

    It used to be served as bytes, with `/landing` answered by an app.yaml
    static handler; that handler is gone, because it would now hand the
    reader the template's own braces. Both paths render the same page.
    """
    from app import web
    from app.models import TotalStatistics

    TotalStatistics(id="total_statistics", games=35295, words_used=417002,
                    by_hour=[0] * (24 * 7)).put()
    web._cache.pop("landing_numbers", None)

    body = client.get("/").text
    # A thousands separator a Russian typographer would accept, not a comma.
    assert "35\u00a0295" in body
    assert "417\u00a0002" in body
    assert "{{" not in body and "{%" not in body
    assert client.get("/landing").text == body


def test_word_statistics_lists_hardest_and_easiest(client, ndb_context):
    for index in range(12):
        GlobalDictionaryWord(id="w{}".format(index), word="w{}".format(index),
                             E=float(index), D=5.0, used_times=index).put()
    response = client.get("/statistics/word_statistics")
    assert response.status_code == 200
    assert "Самые сложные" in response.text
    assert "w11" in response.text


def test_hardest_words_are_ranked_by_the_conservative_estimate(client,
                                                               ndb_context):
    """A barely-played word must not outrank a well-measured one on E alone.

    "новичок" has the higher mu but is still at the prior sigma; "мерка" is
    lower but measured. Ranking by mu - 2*sigma puts "мерка" first, and the
    same in reverse for the easiest table.
    """
    GlobalDictionaryWord(id="новичок", word="новичок", E=80.0, D=50.0 / 3,
                         used_times=2).put()
    GlobalDictionaryWord(id="мерка", word="мерка", E=70.0, D=3.0,
                         used_times=200).put()
    GlobalDictionaryWord(id="лёгкое", word="лёгкое", E=20.0, D=3.0,
                         used_times=200).put()
    response = client.get("/statistics/word_statistics")
    assert response.status_code == 200
    assert response.text.index("мерка") < response.text.index("новичок")
    # The tables show the bound they rank by: 70 - 6 and 20 + 6.
    assert "64.0" in response.text and "26.0" in response.text


def test_word_statistics_for_a_single_word(client, ndb_context):
    GlobalDictionaryWord(id="кот", word="кот", E=61.25, D=4.0, used_times=10,
                         guessed_times=8, failed_times=1,
                         total_explanation_time=80,
                         counts_by_expl_time=[0, 3, 5]).put()
    response = client.get("/statistics/word_statistics", params={"word": "КОТ"})
    assert response.status_code == 200

    # The difficulty is the number the page leads with.
    assert "61.2" in response.text or "61.3" in response.text
    assert 'class="figure__value"' in response.text
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


def test_word_statistics_survives_a_projection_that_is_not_ready(
        client, ndb_context, monkeypatch):
    """The dictionary-wide sections go; the page stays.

    A composite index takes minutes to build over a real dictionary, and
    queries against it fail until it is done — which is what the first
    production deploy met. The page has always caught that; what it handed
    the template was `{}`, and `analytics.outliers.rare_easy` on a missing
    key raises in Jinja rather than reading as empty, so the page 500ed
    anyway. Nothing may be cached either: the next request must try again.
    """
    from app import web

    for index in range(3):
        GlobalDictionaryWord(id="w{}".format(index), word="w{}".format(index),
                             E=float(index), D=5.0, used_times=index + 1).put()
    web._cache.pop("word_analytics", None)

    def not_ready():
        raise Exception("The index for this query is not ready to serve.")

    monkeypatch.setattr(web, "_word_shape", not_ready)
    response = client.get("/statistics/word_statistics")
    assert response.status_code == 200
    assert "Частота — не сложность" not in response.text
    assert "word_analytics" not in web._cache


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
    # The day reaches the page as a column on the chart. It used to be read
    # off the full-history table, which is gone; the chart labels its columns
    # by month and day, the year being the same all the way across.
    assert "11-15" in response.text
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


def test_word_statistics_shows_the_hardest_words_as_slips(client, ndb_context):
    for index in range(12):
        GlobalDictionaryWord(id="w{}".format(index), word="w{}".format(index),
                             E=float(index), D=5.0, used_times=index).put()
    response = client.get("/statistics/word_statistics")
    # The three hardest words are showcased on paper slips above the tables.
    assert 'class="ws ws--honey"' in response.text
    assert "труднее всего объяснить" in response.text


def test_word_statistics_lists_error_prone_words(client, ndb_context):
    """The legacy «ошибкоопасные слова» table, with the error rate computed
    honestly (the stored `danger` property keeps the py27 floor-division bug)."""
    GlobalDictionaryWord(id="каламбур", word="каламбур", E=70.0, D=5.0,
                         used_times=20, guessed_times=8, failed_times=10).put()
    GlobalDictionaryWord(id="кот", word="кот", E=10.0, D=5.0,
                         used_times=20, guessed_times=20, failed_times=0).put()
    # Too few attempts to qualify, even though every one failed.
    GlobalDictionaryWord(id="шум", word="шум", E=50.0, D=5.0,
                         used_times=2, failed_times=2).put()
    response = client.get("/statistics/word_statistics")
    assert "Ошибкоопасные" in response.text
    assert "50%" in response.text
    # The danger table is the last content block; «шум» may appear in the
    # hardest/easiest tables above, but not after the danger caption.
    danger_section = response.text.split("Ошибкоопасные")[1]
    assert "каламбур" in danger_section
    assert "шум" not in danger_section


def test_word_page_draws_the_difficulty_scale(client, ndb_context):
    GlobalDictionaryWord(id="кот", word="кот", E=61.25, D=4.0, used_times=10,
                         guessed_times=8, failed_times=1,
                         total_explanation_time=80,
                         counts_by_expl_time=[0, 3, 5]).put()
    response = client.get("/statistics/word_statistics", params={"word": "кот"})
    # The old gauge, flat: a confidence band E +- 2D and a marker at E.
    assert 'class="scale__band"' in response.text
    assert "left: 53.2%" in response.text          # E - 2D
    assert "left: 61.2%" in response.text          # the marker


def test_total_statistics_ports_the_legacy_extras(client, ndb_context):
    from app.models import WordFrequency

    total = TotalStatistics.get()
    total.games = 42
    total.words_used = 1234
    total.by_hour[5] = 7          # Thursday (index offset +3), 05:00
    total.put()
    # Six words of one length so the by-length chart has a qualifying bucket.
    for index in range(6):
        word = "слово{}".format(index)
        GlobalDictionaryWord(id=word, word=word, E=40.0 + index, D=6.0,
                             used_times=3 + index,
                             total_explanation_time=100 + index).put()
        WordFrequency(id=word, word=word, frequency=5.0).put()

    response = client.get("/statistics/total_statistics")
    assert response.status_code == 200

    # The hour-of-week punchcard: the single non-zero cell is the peak dot.
    assert 'class="punch"' in response.text
    assert "--v: 1.0" in response.text

    # The longest-explained word, on a slip, with a human-readable duration.
    assert "Дольше всего объясняли" in response.text
    assert "слово5" in response.text
    assert "минуту" in response.text               # 105 sec -> 1 минуту 45 секунд

    # The dictionary's own analytics belong to the words page, not this one.
    assert "по длине слова" not in response.text
    assert "частотности" not in response.text


def test_word_statistics_carries_the_analytics(client, ndb_context):
    """The analytics the old site rendered as matplotlib images."""
    from app.models import WordFrequency

    for index in range(6):
        word = "слово{}".format(index)
        GlobalDictionaryWord(id=word, word=word, E=40.0 + index, D=6.0,
                             used_times=3 + index,
                             total_explanation_time=100 + index).put()
        WordFrequency(id=word, word=word, frequency=5.0).put()

    response = client.get("/statistics/word_statistics")
    assert response.status_code == 200
    assert "по длине слова" in response.text
    assert "Насколько точно мы это знаем" in response.text
    assert "частотности" in response.text
    # Difficulty read back in seconds, from a quantity the rating never saw.
    assert "Сколько секунд уходит на слово" in response.text


def test_word_statistics_hides_frequency_without_corpus_data(client, ndb_context):
    GlobalDictionaryWord(id="кот", word="кот", E=40.0, D=6.0, used_times=3).put()
    response = client.get("/statistics/word_statistics")
    assert response.status_code == 200
    assert "частотности" not in response.text
    assert "Частота — не сложность" not in response.text


def test_frequency_outliers_pick_the_words_frequency_gets_wrong(client,
                                                                ndb_context):
    """Rare words that turned out easy, common words that turned out hard —
    the counter-examples to rating a word by how often the language uses it.
    """
    from app.models import WordFrequency

    # Twenty words spread across the frequency range, difficulty rising with
    # frequency, so the plain rule "rare = hard" holds for all of them...
    for index in range(20):
        word = "слово{:02d}".format(index)
        GlobalDictionaryWord(id=word, word=word, E=20.0 + index * 2, D=3.0,
                             used_times=20, guessed_times=18,
                             total_explanation_time=200).put()
        WordFrequency(id=word, word=word, frequency=0.2 + index).put()
    # ...and two that break it, one at each end.
    GlobalDictionaryWord(id="зыбь", word="зыбь", E=9.0, D=3.0, used_times=20,
                         guessed_times=18, total_explanation_time=90).put()
    WordFrequency(id="зыбь", word="зыбь", frequency=0.05).put()
    GlobalDictionaryWord(id="совесть", word="совесть", E=95.0, D=3.0,
                         used_times=20, guessed_times=18,
                         total_explanation_time=600).put()
    WordFrequency(id="совесть", word="совесть", frequency=40.0).put()

    response = client.get("/statistics/word_statistics")
    assert response.status_code == 200
    assert "Редкие, а объяснить легко" in response.text
    assert "Частые, а объяснить трудно" in response.text
    # Both words also appear in the leaderboards above, so read the two
    # lists themselves rather than the first mention on the page.
    rare = response.text.index("Редкие, а объяснить легко")
    common = response.text.index("Частые, а объяснить трудно")
    rare_block = response.text[rare:common]
    common_block = response.text[common:response.text.index("Что ещё видно")]
    assert "зыбь" in rare_block and "совесть" not in rare_block
    assert "совесть" in common_block and "зыбь" not in common_block


def test_frequency_outliers_need_the_bound_not_a_lucky_round(client,
                                                             ndb_context):
    """A barely-played word must not make the easy list on two lucky rounds:
    selection is on E + 2D, so a wide interval keeps it out."""
    from app.models import WordFrequency

    for index in range(20):
        word = "слово{:02d}".format(index)
        GlobalDictionaryWord(id=word, word=word, E=30.0 + index, D=3.0,
                             used_times=20, guessed_times=18,
                             total_explanation_time=200).put()
        WordFrequency(id=word, word=word, frequency=0.2 + index).put()
    # Rare, and looks easiest of all -- on five games and the prior sigma.
    GlobalDictionaryWord(id="новичок", word="новичок", E=12.0, D=50.0 / 3,
                         used_times=5, guessed_times=4,
                         total_explanation_time=40).put()
    WordFrequency(id="новичок", word="новичок", frequency=0.05).put()

    response = client.get("/statistics/word_statistics")
    assert response.status_code == 200
    rare = response.text.index("Редкие, а объяснить легко")
    common = response.text.index("Частые, а объяснить трудно")
    assert "новичок" not in response.text[rare:common]
