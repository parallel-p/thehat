# -*- coding: utf-8 -*-
"""Web pages -- contract 8 of MIGRATION_PLAN.md §5.

Deliberately minimal: no login, no admin, no memcache, no matplotlib plots. The
statistics pages exist because they are linked from elsewhere, and they are now
excluded from crawling by /robots.txt (bots were 3.8k of ~4k monthly hits).
"""

import logging
import os
import random
import threading
import time
from typing import NamedTuple

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.models import (DailyStatistics, GamesForPlayerCount,
                        GlobalDictionaryWord, TotalStatistics, WordFrequency)

logger = logging.getLogger(__name__)

router = APIRouter()

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

CACHE_TTL = 60 * 60  # seconds; replaces the old memcache usage
_cache = {}
_cache_lock = threading.Lock()


def cached(key, producer):
    """Per-instance TTL cache. Good enough for pages nobody but bots reads."""
    now = time.time()
    with _cache_lock:
        entry = _cache.get(key)
        if entry and entry[0] > now:
            return entry[1]
    value = producer()
    with _cache_lock:
        _cache[key] = (now + CACHE_TTL, value)
    return value


LANDING_PAGE = os.path.join(TEMPLATES_DIR, "landing.html")


class Word(NamedTuple):
    """One row of the dictionary as the statistics pages see it."""
    word: str
    E: float
    D: float
    used: int
    failed: int
    guessed: int
    seconds: int

    @property
    def per_attempt(self):
        """Seconds spent explaining this word, per attempt at it."""
        return self.seconds / self.used


def _word_shape():
    """One projection pass over the dictionary.

    A projection stays index-only, so the heavyweight `used_games` lists are
    never loaded. Words never attempted are dropped. Needs the composite
    index on all six properties in index.yaml.
    """
    query = GlobalDictionaryWord.query(
        projection=[GlobalDictionaryWord.E, GlobalDictionaryWord.D,
                    GlobalDictionaryWord.used_times,
                    GlobalDictionaryWord.failed_times,
                    GlobalDictionaryWord.guessed_times,
                    GlobalDictionaryWord.total_explanation_time])
    rows = [Word(entity.key.id(), entity.E, entity.D, entity.used_times,
                 entity.failed_times, entity.guessed_times,
                 entity.total_explanation_time)
            for entity in query.fetch()]
    return [row for row in rows if row.used]


def _frequency_map():
    """word -> corpus frequency (uses per million). Empty if the legacy
    WordFrequency kind is gone from the datastore."""
    try:
        query = WordFrequency.query(projection=[WordFrequency.frequency])
        return {entity.key.id(): entity.frequency for entity in query.fetch()}
    except Exception:  # noqa: BLE001 -- an optional stat must never 500 the page
        logger.exception("WordFrequency unavailable; hiding the frequency stat")
        return {}


# Frequency buckets, in uses per million words (log-ish scale, like the old
# scatter plot's log axis).
_FREQ_BUCKETS = [(0.0, 0.3, "реже 0,3"), (0.3, 1.0, "0,3–1"),
                 (1.0, 3.0, "1–3"), (3.0, 10.0, "3–10"),
                 (10.0, 30.0, "10–30"), (30.0, float("inf"), "чаще 30")]

# Difficulty buckets, for reading the rating back out in seconds.
_E_BUCKETS = [(0.0, 35.0, "до 35"), (35.0, 45.0, "35–45"),
              (45.0, 55.0, "45–55"), (55.0, 65.0, "55–65"),
              (65.0, float("inf"), "выше 65")]

# A pair counts as equally common if the frequencies are within this factor.
_TWIN_RATIO = 1.2
# Both words need enough plays that the gap between them is not noise.
_TWIN_MIN_GAMES = 5


def _frequency_twins(shape, frequencies, limit=3):
    """Pairs of words the language uses about equally often, that the players
    found very differently hard.

    This is the site's whole claim in one object: corpus frequency is what
    other Hat apps rate words by, and here are two words it cannot tell
    apart. Words are used at most once across the pairs, so three pairs are
    six different words.
    """
    candidates = sorted(
        ((frequencies[row.word], row) for row in shape
         if row.used >= _TWIN_MIN_GAMES and frequencies.get(row.word)),
        key=lambda pair: pair[0])

    pairs = []
    for index, (frequency, row) in enumerate(candidates):
        for other_frequency, other in candidates[index + 1:]:
            if other_frequency > frequency * _TWIN_RATIO:
                break        # sorted, so nothing further can be close enough
            pairs.append((abs(row.E - other.E), row, other))

    used = set()
    twins = []
    for _gap, one, other in sorted(pairs, key=lambda pair: -pair[0]):
        if one.word in used or other.word in used:
            continue
        used.update((one.word, other.word))
        harder, easier = sorted((one, other), key=lambda row: -row.E)
        twins.append({
            "harder": {"word": harder.word, "E": harder.E,
                       "sec": harder.per_attempt},
            "easier": {"word": easier.word, "E": easier.E,
                       "sec": easier.per_attempt},
            "frequency": max(frequencies[one.word], frequencies[other.word]),
        })
        if len(twins) == limit:
            break
    return twins


# E and D are a word's TrueSkill mu and sigma (prior 50 +- 50/3, see
# trueskill_env). Ordering the leaderboards by E alone puts words up top that
# are merely unmeasured: two plays with a lucky outcome leave mu high while
# sigma is still near the prior. So rank by the conservative estimate instead,
# mu - k*sigma for the hardest and mu + k*sigma for the easiest -- the same
# "conservative skill estimate" TrueSkill itself uses for leaderboards, which
# there is k = 3. At k = 2 a word must clear ~98% one-sided confidence, and an
# unplayed word scores 50 - 33 = 17, so the prior sinks to the bottom on its
# own and no minimum-games cutoff is needed.
_CONSERVATIVE_SIGMAS = 2.0


def _word_analytics():
    """The analytical stats the old site drew as matplotlib PNGs, plus the
    error-prone-words table, all from one projection pass.

    The stored `danger` property keeps the py27 floor-division bug and is
    ~always 0, so the error rate is computed honestly here instead of
    ordering by that property the way the legacy page did.

    Raises if the projection is unavailable, rather than returning empty:
    the caller degrades to a page without analytics, and because nothing was
    returned nothing is cached, so the next request tries again. Swallowing
    it here would pin an empty page in the cache for the full hour every
    time a composite index is rebuilt.
    """
    shape = _word_shape()

    by_length = {}
    for row in shape:
        length = min(len(row.word), 13)
        by_length.setdefault(length, []).append(row.E)
    length_rows = [
        {"label": "13+" if length == 13 else str(length),
         "avg": sum(es) / len(es), "count": len(es)}
        for length, es in sorted(by_length.items()) if len(es) >= 5]

    d_by_games = {}
    for row in shape:
        d_by_games.setdefault(min(row.used, 8), []).append(row.D)
    d_rows = [
        {"label": "8+" if bucket == 8 else str(bucket),
         "avg": sum(ds) / len(ds), "count": len(ds)}
        for bucket, ds in sorted(d_by_games.items())]

    # The rating against the clock. E is an abstract TrueSkill mu; seconds per
    # attempt is not, and it is measured from a different quantity, so the two
    # agreeing is the evidence that the rating means what it claims.
    sec_groups = [[] for _ in _E_BUCKETS]
    for row in shape:
        for index, (low, high, _label) in enumerate(_E_BUCKETS):
            if low <= row.E < high:
                sec_groups[index].append(row.per_attempt)
                break
    seconds_rows = [
        {"label": label, "avg": sum(ss) / len(ss), "count": len(ss)}
        for (low, high, label), ss in zip(_E_BUCKETS, sec_groups)
        if len(ss) >= 5]
    if not any(row["avg"] for row in seconds_rows):
        seconds_rows = []   # no clock data recorded; the chart would be a lie

    frequencies = _frequency_map()
    freq_groups = [[] for _ in _FREQ_BUCKETS]
    for row in shape:
        frequency = frequencies.get(row.word)
        if frequency is None:
            continue
        for index, (low, high, _label) in enumerate(_FREQ_BUCKETS):
            if low <= frequency < high:
                freq_groups[index].append(row.E)
                break
    freq_rows = [
        {"label": label, "avg": sum(es) / len(es), "count": len(es)}
        for (low, high, label), es in zip(_FREQ_BUCKETS, freq_groups) if es]

    danger = sorted(
        ({"word": row.word, "E": row.E, "share": 100.0 * row.failed / row.used}
         for row in shape if row.used >= 10 and row.failed),
        key=lambda row: -row["share"])[:10]

    # The hardest and easiest words, ranked by the pessimistic end of each
    # word's own interval rather than by E. See _CONSERVATIVE_SIGMAS.
    ranked = [{"word": row.word, "E": row.E, "D": row.D,
               "sec": row.per_attempt} for row in shape]
    hardest = sorted(
        ranked, key=lambda row: -(row["E"] - _CONSERVATIVE_SIGMAS * row["D"])
    )[:10]
    easiest = sorted(
        ranked, key=lambda row: row["E"] + _CONSERVATIVE_SIGMAS * row["D"]
    )[:10]

    return {"by_length": length_rows, "d_by_games": d_rows,
            "by_freq": freq_rows, "by_seconds": seconds_rows,
            "twins": _frequency_twins(shape, frequencies),
            "danger_top": danger, "hardest": hardest, "easiest": easiest}


@router.get("/", response_class=HTMLResponse)
def index():
    """The landing page.

    Served as raw bytes rather than rendered, so that `/` and the static
    `/landing` handler return byte-identical responses. The page has no
    template variables.
    """
    with open(LANDING_PAGE, "rb") as handle:
        return HTMLResponse(content=handle.read())


@router.get("/statistics/word_statistics", response_class=HTMLResponse)
def word_statistics(request: Request, word: str = None):
    entity = GlobalDictionaryWord.get(word) if word else None
    context = {"word": word, "word_entity": entity,
               "top": [], "bottom": [], "rand": []}
    if not entity:
        # Both leaderboards come from the analytics pass, which already reads
        # every played word: they need E and D together, and no datastore
        # ordering can express mu -+ k*sigma anyway.
        try:
            analytics = cached("word_analytics", _word_analytics)
        except Exception:  # noqa: BLE001 -- e.g. the composite index still
            # building right after a deploy. Render the page without the
            # dictionary-wide sections rather than 500, and do not cache that.
            logger.exception("word-shape projection unavailable; hiding analytics")
            analytics = {}
        context["top"] = analytics.get("hardest", [])
        context["bottom"] = analytics.get("easiest", [])
        count = cached(
            "used_words_count",
            lambda: GlobalDictionaryWord.query(
                GlobalDictionaryWord.used_times > 0).count())
        if count >= 10:
            context["rand"] = GlobalDictionaryWord.query(
                GlobalDictionaryWord.used_times > 0).fetch(
                    limit=10, offset=random.randint(0, count - 10))
        # Everything the dictionary knows about itself lives on this page:
        # what a word's difficulty is worth in seconds, why frequency is not
        # difficulty, and what else moves the number. It used to hang off the
        # bottom of the games page, which is about games.
        context["analytics"] = analytics
    return templates.TemplateResponse(request, "word_statistics.html", context)


@router.get("/statistics/total_statistics", response_class=HTMLResponse)
def total_statistics(request: Request):
    total = TotalStatistics.get()
    by_hour = [0] * 24
    by_day = [0] * 7
    # 7x24 punchcard, same hour-of-week layout the old bubble chart used.
    punchcard = [[0] * 24 for _ in range(7)]
    for hour, games in enumerate(total.by_hour or []):
        by_hour[hour % 24] += games
        by_day[(hour // 24 + 3) % 7] += games
        punchcard[(hour // 24 + 3) % 7][hour % 24] += games
    punch_peak = max(max(row) for row in punchcard)

    daily = cached(
        "daily",
        lambda: [(el.date.strftime("%Y-%m-%d"), el.games, el.words_used,
                  el.players_participated, el.total_game_duration // 60)
                 for el in DailyStatistics.query().order(
                     DailyStatistics.date).fetch()])
    daily_recent = [(row[0], row[1]) for row in daily[-84:]]

    # What one game looks like, averaged over the days we have records for.
    logged_games = sum(row[1] for row in daily)
    per_game = {
        "words": sum(row[2] for row in daily) / logged_games,
        "minutes": sum(row[4] for row in daily) / logged_games,
        "players": sum(row[3] for row in daily) / logged_games,
    } if logged_games else None

    longest = cached(
        "longest_explanation",
        lambda: GlobalDictionaryWord.query().order(
            -GlobalDictionaryWord.total_explanation_time).get())

    context = {
        "words_in_dictionary": cached(
            "dict_word", lambda: GlobalDictionaryWord.query().count()),
        "used_words": cached(
            "used_words",
            lambda: GlobalDictionaryWord.query(
                GlobalDictionaryWord.used_times > 0).count()),
        "total_words": total.words_used,
        "total_games": total.games,
        "games_for_players": cached(
            "for_player_count",
            lambda: GamesForPlayerCount.query().order(
                GamesForPlayerCount.player_count).fetch()),
        "daily": daily,
        "daily_recent": daily_recent,
        "daily_recent_peak": max((games for _date, games in daily_recent),
                                 default=0),
        "by_hour": by_hour,
        "by_day": by_day,
        "punchcard": punchcard,
        "punch_peak": punch_peak,
        "longest_word": longest.word if longest else None,
        "longest_time": longest.total_explanation_time if longest else 0,
        "per_game": per_game,
    }
    return templates.TemplateResponse(request, "total_statistics.html", context)


@router.get("/_ah/warmup", include_in_schema=False)
def warmup():
    """Sent by App Engine to a fresh instance; needs `inbound_services: warmup`."""
    return {"status": "ok"}


@router.get("/_status", include_in_schema=False)
def status():
    """Deploy smoke check.

    Not `/healthz`: App Engine's frontend reserves that path and answers it
    itself, so a route there is unreachable.
    """
    return {"status": "ok"}
