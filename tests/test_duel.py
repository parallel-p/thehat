# -*- coding: utf-8 -*-
"""The daily word duel at /duel."""

import datetime
import json

import pytest

from app import duel, web
from app.models import GlobalDictionaryWord, WordDuel, WordFrequency


def make_dictionary(count=400, used=20, spread=0.1, sigma=0.4,
                    frequencies=True):
    """`count` well-measured words spaced `spread` apart in difficulty.

    Finely spaced, so that every gap band has something in it, and given
    corpus frequencies by default -- the harder half of the ramp needs two
    words of comparable frequency and cannot be built without them.
    """
    for index in range(count):
        word = "слово{}".format(index)
        GlobalDictionaryWord(id=word, word=word, E=20.0 + index * spread,
                             D=sigma, used_times=used, guessed_times=used,
                             failed_times=0, total_explanation_time=used * 10).put()
        if frequencies:
            WordFrequency(id=word, word=word, frequency=1.0).put()


def pool_of(*words):
    """A pool literal: (word, E, D, frequency) rows.

    A bare (word, E, D) is padded with a frequency of 1.0, which makes every
    pair frequency-neutral -- what most of these tests want, since they are
    about the gap ramp and not about the cue.
    """
    return [tuple(row) + (1.0,) * (4 - len(row)) for row in words]


# --------------------------------------------------------------------------
# The bar a pair has to clear
# --------------------------------------------------------------------------


def test_a_pair_needs_a_gap_worth_asking_about():
    """Two words a point apart are different and nobody could tell."""
    assert not duel._separated(("а", 50.0, 0.01), ("б", 51.0, 0.01))
    assert duel._separated(("а", 50.0, 0.01), ("б", 60.0, 0.01))


def test_a_pair_needs_the_gap_to_outrun_the_uncertainty():
    """A wide gap between two barely-measured words proves nothing.

    Both pairs are 10 points apart. The first is two words at the prior
    sigma -- a word nobody has played -- and 10 points is well inside the
    noise; the second is two words the server has watched.
    """
    prior = 50.0 / 3
    assert not duel._separated(("а", 50.0, prior), ("б", 60.0, prior))
    assert duel._separated(("а", 50.0, 2.0), ("б", 60.0, 2.0))


def test_the_confidence_threshold_is_the_one_advertised():
    """`_Z` is the z at which the normal CDF reaches `_CONFIDENCE`."""
    assert duel._phi(duel._Z) == pytest.approx(duel._CONFIDENCE, abs=1e-9)
    # The page tells readers 90%; if that constant moves, the page is wrong.
    assert duel._CONFIDENCE == 0.9


# --------------------------------------------------------------------------
# Choosing a day
# --------------------------------------------------------------------------


def dense_pool(count=600, step=0.1, sigma=0.4):
    """A pool fine-grained enough that every gap band can be filled.

    A tenth of a point, so that even the narrowest band (0.3 wide) has
    several distinct gaps in it and the sampler is not relying on one; and a
    sigma small enough that the confidence test passes at `_MIN_GAP` --
    otherwise these tests would be exercising the band-widening fallback
    rather than the ramp. Tenths also survive the one-decimal rounding
    `choose_pairs` stores ratings at.
    """
    return pool_of(*[("w{}".format(i), i * step, sigma) for i in range(count)])


def test_a_day_is_ten_pairs_of_twenty_different_words():
    pairs = duel.choose_pairs(dense_pool(), [], datetime.date(2026, 8, 3))

    assert len(pairs) == duel.PAIRS_PER_DAY
    words = [word for pair in pairs for word in pair[:2]]
    assert len(set(words)) == 2 * duel.PAIRS_PER_DAY


def test_the_day_is_a_ramp_from_obvious_to_barely_there():
    """The whole shape of the game: each pair is closer than the last.

    Not merely "sorted" -- each gap has to land in its own band, which is
    what makes the first pair obvious and the last one genuinely at the edge.
    """
    pairs = duel.choose_pairs(dense_pool(), [], datetime.date(2026, 8, 3))
    gaps = [abs(pair[3] - pair[4]) for pair in pairs]

    assert gaps == sorted(gaps, reverse=True)
    for gap, (low, high, _neutral) in zip(gaps, duel._GAP_BANDS):
        assert low <= gap < high

    # And the ends are where the page says they are.
    assert 6.6 <= gaps[0] < 7.6
    assert gaps[-1] < 2.6


def spread_frequencies(count=600, step=0.1, sigma=0.4):
    """A pool where corpus frequency varies wildly from word to word.

    Neighbouring words are three times apart in frequency, so a pair can only
    be frequency-neutral by being drawn from a narrow slice of the pool --
    which is what the harder bands have to do.
    """
    return pool_of(*[("w{}".format(i), i * step, sigma, 3.0 ** (i % 12))
                     for i in range(count)])


def test_the_hard_half_takes_the_frequency_cue_away():
    """The second axis of the ramp.

    Left alone, "the rarer word is the harder one" is right about 61% of the
    time and a reader can play well knowing nothing about the ratings. The
    bands marked neutral require the two words to be within `_NEAR_RATIO`,
    which is what makes that cue worth nothing.
    """
    pool = spread_frequencies()
    frequencies = {word: f for word, _E, _D, f in pool}
    pairs = duel.choose_pairs(pool, [], datetime.date(2026, 8, 3))

    for pair, (_low, _high, neutral) in zip(pairs, duel._GAP_BANDS):
        if not neutral:
            continue
        one, other = frequencies[pair[0]], frequencies[pair[1]]
        assert max(one, other) / min(one, other) <= duel._NEAR_RATIO


def test_a_pair_with_no_frequency_at_all_is_never_called_neutral():
    """`None` is not "close enough"; it is "cannot be shown either way"."""
    known = ("а", 50.0, 1.0, 4.0)
    assert duel._similarly_common(known, ("б", 53.0, 1.0, 4.5), 1.6)
    assert not duel._similarly_common(known, ("б", 53.0, 1.0, 40.0), 1.6)
    assert not duel._similarly_common(known, ("б", 53.0, 1.0, None), 1.6)
    assert not duel._similarly_common(known, ("б", 53.0, 1.0, 0.0), 1.6)


def test_a_pool_stored_before_frequencies_existed_still_works(client,
                                                              ndb_context):
    """The stored blob outlives the deploy that wrote it, by up to two days.

    A row one column short is what the previous version wrote; reading it
    must mean "frequency unknown", not an index error on the first generation
    after a deploy.
    """
    from app import web

    web._write_shared("duel_pool",
                      [["w{}".format(i), i * 0.1, 0.4] for i in range(600)])
    web._cache.clear()

    pool = duel._pool()
    assert all(len(row) == 4 for row in pool)
    assert all(row[3] is None for row in pool)
    assert len(duel.choose_pairs(pool, [], datetime.date(2026, 8, 3))) \
        == duel.PAIRS_PER_DAY


def test_a_dictionary_without_frequencies_still_gets_a_puzzle():
    """An easier question is worth more than no question.

    `_similarly_common` is False whenever a frequency is missing, and no
    loosening of the ratio changes that -- so without this fallback the loss
    of the legacy WordFrequency kind would leave the page permanently empty
    rather than merely easier.
    """
    pool = pool_of(*[("w{}".format(i), i * 0.1, 0.4, None) for i in range(600)])
    pairs = duel.choose_pairs(pool, [], datetime.date(2026, 8, 3))

    assert len(pairs) == duel.PAIRS_PER_DAY
    gaps = [abs(pair[3] - pair[4]) for pair in pairs]
    # The gap ramp is untouched by the frequency half giving way.
    assert gaps == sorted(gaps, reverse=True)


def test_the_hardest_pair_is_still_a_pair_with_an_answer():
    """The bottom of the ramp is hard, not arbitrary.

    Every band, including the last, is above `_MIN_GAP` and clears the
    confidence test -- a question nobody can see is still a question with a
    right answer.
    """
    for low, _high, _neutral in duel._GAP_BANDS:
        assert low >= duel._MIN_GAP
    assert duel._separated(("а", 0.0, 1.23), ("б", duel._MIN_GAP, 1.23))


def test_every_pair_names_the_harder_word_and_its_rating():
    pool = dense_pool()
    ratings = {word: E for word, E, _D, _frequency in pool}

    for left, right, harder, e_left, e_right in duel.choose_pairs(
            pool, [], datetime.date(2026, 8, 3)):
        assert harder in (0, 1)
        # The flagged word is the one with the higher rating...
        assert ratings[[left, right][harder]] > ratings[[left, right][1 - harder]]
        # ...and the ratings travelling with the pair are its own.
        assert e_left == pytest.approx(ratings[left], abs=0.05)
        assert e_right == pytest.approx(ratings[right], abs=0.05)


def test_the_harder_word_is_not_always_on_the_same_side():
    """A quiz whose answer is always the left slip is not a quiz."""
    pool = dense_pool()
    sides = set()
    for offset in range(6):
        date = datetime.date(2026, 8, 3) + datetime.timedelta(days=offset)
        sides.update(pair[2] for pair in duel.choose_pairs(pool, [], date))
    assert sides == {0, 1}


def test_every_chosen_pair_clears_the_bar():
    """On a pool where the overwhelming majority of pairs do not.

    The bands are narrow -- the last one is 0.3 points wide out of a 300
    point spread -- so the sampler has to be rejecting nearly everything it
    draws rather than taking the first two words it saw.
    """
    pool = dense_pool()
    for pair in duel.choose_pairs(pool, [], datetime.date(2026, 8, 3)):
        left, right = pair[0], pair[1]
        assert duel._separated((left, pair[3], 0.4), (right, pair[4], 0.4))


def test_a_pool_that_cannot_make_a_puzzle_says_so():
    """Ten identical words are ten words, and no pairs."""
    pool = pool_of(*[("w{}".format(i), 50.0, 1.0) for i in range(60)])
    with pytest.raises(duel.NotEnoughWords):
        duel.choose_pairs(pool, [], datetime.date(2026, 8, 3))


def test_the_same_day_and_pool_choose_the_same_puzzle():
    """The choice is a function of the day, not of when the day was asked."""
    pool = dense_pool()
    date = datetime.date(2026, 8, 3)
    assert duel.choose_pairs(pool, [], date) == duel.choose_pairs(pool, [], date)
    assert duel.choose_pairs(pool, [], date) != duel.choose_pairs(
        pool, [], date + datetime.timedelta(days=1))


# --------------------------------------------------------------------------
# Not asking the same word twice
# --------------------------------------------------------------------------


def past_puzzle(day, pairs):
    return WordDuel(id="d{}".format(day), day=day, pairs=pairs)


def test_a_word_already_asked_is_not_asked_again(ndb_context):
    pool = dense_pool()
    date = datetime.date(2026, 8, 3)

    first = duel.choose_pairs(pool, [], date)
    spent = {word for pair in first for word in pair[:2]}

    second = duel.choose_pairs(pool, [past_puzzle(1, first)],
                               date + datetime.timedelta(days=1))
    assert not spent & {word for pair in second for word in pair[:2]}


def test_the_oldest_day_comes_back_first_when_the_pool_runs_out(ndb_context):
    """The dictionary is finite; "never again" cannot be kept for ever.

    What is kept: a word only returns once everything else has been used, and
    the puzzle it returns from is the oldest one on record.
    """
    # Sized so that the two spent days are what put the pool under the
    # reserve, and forgiving the older of them is enough to clear it again.
    size = duel._RESERVE + 5
    pool = pool_of(*[("w{}".format(i), float(i * 3), 1.0) for i in range(size)])
    oldest = [["w0", "w1", 1, 0.0, 3.0], ["w2", "w3", 1, 6.0, 9.0]]
    newest = [["w4", "w5", 1, 12.0, 15.0], ["w6", "w7", 1, 18.0, 21.0]]

    fresh = duel._fresh_words(pool, [past_puzzle(1, oldest),
                                     past_puzzle(2, newest)])
    words = {row[0] for row in fresh}

    # Day 1 comes back and day 2 does not: forgiveness stops the moment there
    # is room, so yesterday's words stay spent for as long as anything else
    # is available.
    assert {"w0", "w1", "w2", "w3"} <= words
    assert not {"w4", "w5", "w6", "w7"} & words


def test_a_pool_smaller_than_the_reserve_forgives_everything(ndb_context):
    """Twenty words a day out of sixty is repetition however it is arranged.

    A staging project or a dictionary nobody has played is the case this
    covers: the alternative to recycling everything is no puzzle at all.
    """
    pool = pool_of(*[("w{}".format(i), float(i * 3), 1.0) for i in range(60)])
    spent = [["w{}".format(i), "w{}".format(i + 1), 1, 0.0, 3.0]
             for i in range(0, 8, 2)]
    words = {row[0] for row in duel._fresh_words(pool, [past_puzzle(1, spent)])}
    assert len(words) == 60


def test_nothing_is_recycled_while_there_is_room(ndb_context):
    pool = pool_of(*[("w{}".format(i), float(i * 3), 1.0) for i in range(400)])
    spent = [["w0", "w1", 1, 0.0, 3.0]]
    words = {row[0] for row in duel._fresh_words(pool, [past_puzzle(1, spent)])}
    assert not {"w0", "w1"} & words


# --------------------------------------------------------------------------
# Storing it
# --------------------------------------------------------------------------


def test_a_day_is_generated_once_and_then_read(ndb_context):
    make_dictionary()
    web._cache.clear()
    date = datetime.date(2026, 8, 3)

    first = duel.puzzle_for(date)
    second = duel.puzzle_for(date)

    assert first.pairs == second.pairs
    assert first.day == duel.day_number(date)
    assert WordDuel.query().count() == 1


def test_a_second_writer_for_one_day_loses(ndb_context):
    """Two readers arriving together must not end up with two puzzles.

    `_claim` is the get-or-create, and this is the case it exists for: the
    puzzle was written between one caller building its pairs and storing them.
    """
    date = datetime.date(2026, 8, 3)
    mine = [["а", "б", 1, 40.0, 50.0]]
    theirs = [["в", "г", 0, 60.0, 50.0]]

    duel._claim(date, theirs)
    assert duel._claim(date, mine).pairs == theirs


def test_day_numbering_starts_at_one(ndb_context):
    assert duel.day_number(duel.EPOCH) == 1
    assert duel.day_number(duel.EPOCH + datetime.timedelta(days=41)) == 42


# --------------------------------------------------------------------------
# The pool the puzzle draws on
# --------------------------------------------------------------------------


def test_the_pool_leaves_out_barely_played_words(client, ndb_context):
    GlobalDictionaryWord(id="частое", word="частое", E=60.0, D=2.0,
                         used_times=web._DUEL_MIN_GAMES, guessed_times=8,
                         failed_times=0, total_explanation_time=100).put()
    GlobalDictionaryWord(id="редкое", word="редкое", E=60.0, D=2.0,
                         used_times=web._DUEL_MIN_GAMES - 1, guessed_times=1,
                         failed_times=0, total_explanation_time=10).put()
    web._cache.clear()

    words = {row[0] for row in web.cached("duel_pool")}
    assert "частое" in words
    assert "редкое" not in words


def test_the_dictionary_is_read_once_for_the_whole_refresh(client, ndb_context,
                                                           monkeypatch):
    """Three of the cached values are built out of the same projection pass.

    It is 20 of the refresh's 30 seconds, so reading it once per value would
    be reading every word in the dictionary three times over.
    """
    make_dictionary(count=40)
    real = web._word_shape
    calls = []

    def counted():
        calls.append(1)
        return real()

    monkeypatch.setattr(web, "_word_shape", counted)
    web.refresh_all()
    assert len(calls) == 1


# --------------------------------------------------------------------------
# The page
# --------------------------------------------------------------------------


def test_the_page_carries_todays_puzzle(client, ndb_context):
    make_dictionary()
    web._cache.clear()

    response = client.get("/duel")
    assert response.status_code == 200
    assert "Что" in response.text

    payload = json.loads(
        response.text.split('id="puzzle">')[1].split("</script>")[0])
    assert payload["day"] == duel.day_number(duel.today())
    assert payload["date"] == duel.today().isoformat()
    assert len(payload["pairs"]) == duel.PAIRS_PER_DAY


def test_the_page_is_not_cached_across_the_midnight_it_turns_over(client,
                                                                  ndb_context):
    make_dictionary()
    web._cache.clear()
    assert client.get("/duel").headers["cache-control"] == "no-cache"


def test_the_page_renders_when_there_is_no_puzzle_to_be_had(client, ndb_context):
    """An empty dictionary is a page that says so, not a 500."""
    web._cache.clear()
    response = client.get("/duel")
    assert response.status_code == 200
    assert "ещё не готовы" in response.text
    assert ">null</script>" in response.text
    assert WordDuel.query().count() == 0


def test_the_puzzle_json_cannot_end_the_script_element():
    """A word is dictionary-curated, but the escaping is not a matter of trust.

    Inside a <script> the browser does not decode entities, so Jinja's
    escaping would break the JSON instead of protecting it; escaping the
    three characters that can start markup leaves JSON that still parses.
    """
    text = duel.payload_json({"pairs": [["</script><img src=x>", "б", 1]]})
    assert "<" not in text and ">" not in text and "&" not in text
    assert json.loads(text)["pairs"][0][0] == "</script><img src=x>"


def test_the_pages_link_to_it(client, ndb_context):
    for path in ("/", "/statistics/word_statistics"):
        assert 'href="/duel"' in client.get(path).text
