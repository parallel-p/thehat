# -*- coding: utf-8 -*-
"""Web pages -- contract 8 of MIGRATION_PLAN.md §5.

Deliberately minimal: no login, no admin, no memcache, no matplotlib plots. The
statistics pages exist because they are linked from elsewhere, and they are now
excluded from crawling by /robots.txt (bots were 3.8k of ~4k monthly hits).
"""

import datetime
import json
import logging
import os
import random
import threading
import time
from typing import NamedTuple

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from google.cloud import ndb

from app.models import (DailyStatistics, GamesForPlayerCount,
                        GlobalDictionaryWord, StatsCache, TotalStatistics,
                        WordFrequency)

logger = logging.getLogger(__name__)

router = APIRouter()

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

CACHE_TTL = 60 * 60  # seconds; replaces the old memcache usage
_cache = {}
_cache_lock = threading.Lock()


# How stale a stored blob may be before a page recomputes it rather than serve
# it. The cron runs daily, so anything past two days means the cron has not
# been running -- at which point one visitor waits and the cache heals itself,
# which is better than serving numbers that quietly stop moving.
STALE_AFTER = datetime.timedelta(days=2)

# key -> the function that computes it. The daily refresh iterates this, so a
# value added here is refreshed by the cron the day it is written; there is no
# second list to keep in step.
_PRODUCERS = {}

_MISSING = object()


def producer(key):
    """Register the function that computes one cached value."""
    def register(function):
        _PRODUCERS[key] = function
        return function
    return register


def _normalise(value):
    """Round-trip through JSON the way the stored copy will be.

    Both paths then hand the templates the same shapes -- tuples come back as
    lists, ints keyed by name stay ints -- so a page cannot behave one way on
    the instance that computed a value and another way everywhere else. That
    difference is exactly the kind that shows up only in production.
    """
    return json.loads(json.dumps(value))


def _utcnow():
    """Naive UTC, which is what ndb stores DateTimeProperty as."""
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def _read_shared(key):
    """The stored blob, or `_MISSING` if absent, stale, or unreadable."""
    try:
        entity = ndb.Key(StatsCache, key).get()
    except Exception:  # noqa: BLE001 -- the cache is an optimisation; if
        # Datastore cannot answer, the page computes its own numbers.
        logger.exception("StatsCache unreadable for %s", key)
        return _MISSING
    if entity is None or entity.payload is None or entity.computed is None:
        return _MISSING
    age = _utcnow() - entity.computed
    if age > STALE_AFTER:
        logger.warning("StatsCache %s is %s old; recomputing. Is the daily "
                       "refresh cron running?", key, age)
        return _MISSING
    return entity.payload


def _write_shared(key, value):
    try:
        StatsCache(id=key, payload=value, computed=_utcnow()).put()
    except Exception:  # noqa: BLE001 -- see above; failing to *store* the
        # answer must not stop us returning it.
        logger.exception("could not store StatsCache %s", key)


def cached(key):
    """The value for `key`: this instance's copy, the shared one, or fresh.

    Three levels, cheapest first. The in-process dict saves a Datastore read
    per request; the StatsCache entity saves the recomputation, and is what
    the daily cron keeps warm; computing inline is the fallback that makes
    the other two optional.
    """
    now = time.time()
    with _cache_lock:
        entry = _cache.get(key)
        if entry and entry[0] > now:
            return entry[1]
    value = _read_shared(key)
    if value is _MISSING:
        value = _normalise(_PRODUCERS[key]())
        # Worth a line: this is the slow path, and after the cron has run once
        # it should only ever be a new key or a genuinely empty cache.
        logger.info("computed %s inline in %.2fs", key, time.time() - now)
        _write_shared(key, value)
    with _cache_lock:
        _cache[key] = (now + CACHE_TTL, value)
    return value


def refresh_all():
    """Recompute every cached value and store it. What the daily cron calls.

    One failure does not stop the others: a page whose numbers are missing
    degrades on its own, and there is no reason to let it take the rest of
    the refresh down with it.
    """
    done, failed = [], []
    for key in list(_PRODUCERS):
        started = time.time()
        try:
            _write_shared(key, _normalise(_PRODUCERS[key]()))
        except Exception:  # noqa: BLE001
            logger.exception("refresh of %s failed", key)
            failed.append(key)
            continue
        done.append("{}={:.2f}s".format(key, time.time() - started))
    with _cache_lock:
        # This instance is serving too, and has just been told the answers.
        _cache.clear()
    logger.info("statistics refresh: %s%s", " ".join(done),
                "; failed: " + " ".join(failed) if failed else "")
    return {"refreshed": len(done), "failed": failed}


# --------------------------------------------------------------------------
# Counting and summing without reading the rows
# --------------------------------------------------------------------------

# Datastore has run COUNT/SUM server-side for years, but google-cloud-ndb 2.5
# never grew an API for it: `Query.count()` still fetches every key and takes
# len(), and its own docstring says so. Counting the dictionary that way cost
# 1.8s of the statistics page's 4.9s, and summing five thousand daily rows to
# print three averages cost 2.2s more. The aggregation API answers all of it
# in one round trip each, so it is worth reaching past ndb to the datastore
# client underneath -- which is already installed, being ndb's own dependency.
#
# The Datastore *emulator* does not implement RunAggregationQuery (501
# MethodNotImplemented). That is what `_aggregate` returning None means, and
# every caller keeps the scan it used to do as its fallback: under `make test`
# the old path is what runs, and it is still the path being asserted on.
_datastore_client = None
_datastore_lock = threading.Lock()
# Off against the emulator from the start: it answers RunAggregationQuery with
# a 501, and building a client to hear that would shell out to `gcloud auth
# print-access-token` first -- which is both slow and the one thing the test
# fixtures promise never to do. Otherwise on, and latched off the first time a
# backend does say it has no aggregation API. Only MethodNotImplemented
# latches; anything else (a quota blip, a transient unavailable) falls back for
# that one call and is tried again on the next.
_aggregations_supported = not os.environ.get("DATASTORE_EMULATOR_HOST")


def _raw_datastore():
    global _datastore_client
    with _datastore_lock:
        if _datastore_client is None:
            from google.cloud import datastore

            from app import settings
            from app.gcp_auth import credentials
            _datastore_client = datastore.Client(project=settings.PROJECT_ID,
                                                 credentials=credentials())
    return _datastore_client


def _aggregate(kind, aggregations, condition=None):
    """Run server-side aggregations over `kind`; None if unsupported.

    `aggregations` is a list of (alias, kind_of_aggregation, property), where
    property is None for a count. `condition` is an optional
    (property, operator, value) filter.
    """
    global _aggregations_supported
    if not _aggregations_supported:
        return None
    try:
        from google.cloud.datastore.query import PropertyFilter

        client = _raw_datastore()
        query = client.query(kind=kind)
        if condition is not None:
            query.add_filter(filter=PropertyFilter(*condition))
        aggregation_query = client.aggregation_query(query)
        for alias, how, prop in aggregations:
            if how == "count":
                aggregation_query.count(alias=alias)
            else:
                aggregation_query.sum(prop, alias=alias)
        batches = list(aggregation_query.fetch())
    except Exception as error:  # noqa: BLE001 -- an optimisation must never be
        # the reason a page 500s. The emulator's 501 comes through here, and so
        # would a permissions or quota problem; the caller scans instead.
        from google.api_core.exceptions import MethodNotImplemented

        if isinstance(error, MethodNotImplemented):
            _aggregations_supported = False
            logger.info("no aggregation API here; statistics will scan instead")
        else:
            logger.warning("aggregation over %s failed; scanning instead",
                           kind, exc_info=True)
        return None
    if not batches:
        return None
    return {result.alias: result.value for result in batches[0]}




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

# A word needs this many plays before its place in the language is worth
# arguing about; past that the +- 2*sigma bounds do the rest of the work.
_OUTLIER_MIN_GAMES = 5
# "Rare" and "common" are the outer quarters of the words we have a corpus
# frequency for -- taken from the data rather than fixed, because what counts
# as rare depends on which corpus the legacy importer used.
_OUTLIER_QUARTILE = 0.25


def _frequency_outliers(shape, frequencies, limit=3):
    """The words that corpus frequency gets most wrong, both ways round.

    Rare words that turn out easy, and common words that turn out hard --
    the counter-examples to rating a word by how often the language uses it.
    Picked on the conservative end of each word's interval (E + 2D for the
    easy claim, E - 2D for the hard one) so that a word cannot make either
    list on two lucky rounds: to be listed as easy it has to be easy even
    read pessimistically.
    """
    known = sorted(
        ((frequencies[row.word], row) for row in shape
         if row.used >= _OUTLIER_MIN_GAMES and frequencies.get(row.word)),
        key=lambda pair: pair[0])
    if len(known) < 4 * limit:
        return {"rare_easy": [], "common_hard": []}

    edge = max(limit, int(len(known) * _OUTLIER_QUARTILE))

    def present(pair):
        frequency, row = pair
        return {"word": row.word, "E": row.E, "sec": row.per_attempt,
                "frequency": frequency}

    return {
        "rare_easy": [present(p) for p in sorted(
            known[:edge], key=lambda p: p[1].E + _CONSERVATIVE_SIGMAS * p[1].D
        )[:limit]],
        "common_hard": [present(p) for p in sorted(
            known[-edge:], key=lambda p: -(p[1].E - _CONSERVATIVE_SIGMAS * p[1].D)
        )[:limit]],
    }


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


def _seconds_by_difficulty(shape):
    """The rating in seconds, per difficulty bucket.

    E is built out of these seconds -- every rating pass in stats ranks a
    game's words by explanation time -- but only out of their *order* within
    one game, so the scale itself carries no unit. This is what a point on it
    is worth on a stopwatch.

    Shared by the statistics page and by /api/v2/word_seconds, which is how
    the app at /play can say what a difficulty setting costs without carrying
    a copy of these numbers that goes stale.
    """
    groups = [[] for _ in _E_BUCKETS]
    for row in shape:
        for index, (low, high, _label) in enumerate(_E_BUCKETS):
            if low <= row.E < high:
                groups[index].append(row.per_attempt)
                break
    rows = [
        {"label": label, "low": low,
         # null, not inf: json.dumps writes a bare `Infinity` for it, which
         # Python reads back happily and every JSON parser on the other side
         # rejects. The last bucket simply has no upper bound.
         "high": None if high == float("inf") else high,
         "avg": sum(times) / len(times), "count": len(times)}
        for (low, high, label), times in zip(_E_BUCKETS, groups)
        if len(times) >= 5]
    # No clock data recorded at all: a chart of zeroes would be a lie.
    return rows if any(row["avg"] for row in rows) else []


def _seconds_curve(shape):
    """Average seconds per attempt at every difficulty from 0 to 100.

    The five buckets above are what a bar chart wants; a slider wants a
    reading at the point it is standing on. One difficulty on its own is thin
    — the corpus is a few thousand rated words over 101 points — so each
    reading is taken over a window either side of the point, widened until it
    has something to average. The window is what makes the curve legible: a
    per-point mean of ten words jumps by seconds between neighbours, and the
    number under a slider that jumps is worse than no number.

    `count` travels with each point so that thinness stays visible rather
    than being smoothed into looking like data.
    """
    at_point = [[] for _ in range(101)]
    for row in shape:
        point = int(round(row.E))
        if 0 <= point <= 100:
            at_point[point].append(row.per_attempt)

    rows = []
    for point in range(101):
        for window in (3, 6, 12, 25):
            times = [time
                     for index in range(max(0, point - window),
                                        min(101, point + window + 1))
                     for time in at_point[index]]
            if len(times) >= 20:
                break
        if not times:
            continue        # nothing anywhere near this difficulty
        rows.append({"d": point, "avg": sum(times) / len(times),
                     "count": len(times)})
    return rows if any(row["avg"] for row in rows) else []


@producer("word_seconds")
def _word_seconds_curve():
    return _seconds_curve(_word_shape())


def word_seconds():
    """The curve on its own, cached like the pages that draw the buckets."""
    return cached("word_seconds")


@producer("word_analytics")
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

    seconds_rows = _seconds_by_difficulty(shape)

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
            "outliers": _frequency_outliers(shape, frequencies),
            "danger_top": danger, "hardest": hardest, "easiest": easiest,
            # Every played word, so the page can draw a real random sample
            # without a query of its own. See `word_statistics`. Pairs rather
            # than the four-key rows above: this is the whole dictionary and
            # it is stored, and the sample shows a word and its difficulty.
            "pool": [[row.word, row.E] for row in shape]}


def _no_analytics():
    """What the page gets when the projection is unavailable.

    The same keys `_word_analytics` returns, all empty. Not `{}`: the page
    reads `analytics.outliers.rare_easy`, and in Jinja an attribute of a
    missing key is not a falsy test but an UndefinedError — which turned the
    degraded page into exactly the 500 the degradation exists to avoid. Seen
    on the first production deploy, where the composite index was still
    building.
    """
    return {"by_length": [], "d_by_games": [], "by_freq": [], "by_seconds": [],
            "outliers": {"rare_easy": [], "common_hard": []},
            "danger_top": [], "hardest": [], "easiest": [], "pool": []}


def _thousands(number):
    """35295 -> "35 295", with the space Russian typography wants."""
    return "{:,}".format(number).replace(",", "\u00a0")


@producer("landing_numbers")
def _landing_numbers():
    """The two figures the landing page shows.

    words_used counts every word a game got through, so it is explanations —
    the same word coming out of the hat in another game counts again. That is
    the number the dataset is measured in, not the size of the dictionary.
    """
    total = TotalStatistics.get()
    return {
        "total_games": _thousands(total.games),
        "total_explanations": _thousands(total.words_used),
    }


@router.get("/", response_class=HTMLResponse)
@router.get("/landing", response_class=HTMLResponse)
def index(request: Request):
    """The landing page.

    Rendered, not served as bytes. The page says how many games the server
    has recorded and how many words those games explained, and those are the
    whole of its argument for existing — a number kept true by remembering to
    edit it is a number that is wrong. Both come off the one TotalStatistics
    entity and are cached for an hour like everything else here, so the
    most-visited page on the site costs at most one datastore read an hour.

    `/landing` is the same page: it used to be an app.yaml static handler,
    which would now serve the template's own braces to the reader.
    """
    numbers = cached("landing_numbers")
    return templates.TemplateResponse(request, "landing.html", dict(numbers))


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
            analytics = cached("word_analytics")
        except Exception:  # noqa: BLE001 -- e.g. the composite index still
            # building right after a deploy. Render the page without the
            # dictionary-wide sections rather than 500, and do not cache that.
            logger.exception("word-shape projection unavailable; hiding analytics")
            analytics = _no_analytics()
        context["top"] = analytics.get("hardest", [])
        context["bottom"] = analytics.get("easiest", [])
        # A real sample, not a window: an offset into an ordered query returns
        # ten neighbours, which on this kind means ten words that happen to sit
        # next to each other in the index — the same clump on every reload for
        # the same offset, and never a spread across the dictionary. The
        # analytics pass has already read every played word, so drawing from
        # its cached list is both uniform and free of a datastore round-trip.
        pool = analytics.get("pool", [])
        if len(pool) >= 10:
            context["rand"] = [{"word": word, "E": difficulty}
                               for word, difficulty in random.sample(pool, 10)]
        # Everything the dictionary knows about itself lives on this page:
        # what a word's difficulty is worth in seconds, why frequency is not
        # difficulty, and what else moves the number. It used to hang off the
        # bottom of the games page, which is about games.
        context["analytics"] = analytics
    return templates.TemplateResponse(request, "word_statistics.html", context)


@producer("dict_word")
def _dictionary_size():
    """How many words the dictionary holds."""
    counted = _aggregate("GlobalDictionaryWord", [("n", "count", None)])
    if counted is not None:
        return int(counted["n"])
    return GlobalDictionaryWord.query().count()


@producer("used_words")
def _played_words():
    """How many of them have ever come out of a hat."""
    counted = _aggregate("GlobalDictionaryWord", [("n", "count", None)],
                         condition=("used_times", ">", 0))
    if counted is not None:
        return int(counted["n"])
    return GlobalDictionaryWord.query(
        GlobalDictionaryWord.used_times > 0).count()


# The daily chart's width. Fetching the tail is the whole point of the number:
# the page used to read every day since 2014 and then slice off the last 84.
_RECENT_DAYS = 84


@producer("longest_explanation")
def _longest_explanation():
    """The word the server has spent the most seconds on, as plain data.

    The entity itself cannot go in the cache -- it is stored as JSON, and it
    carries a `used_games` list thousands of entries long that the page has
    no use for.
    """
    word = GlobalDictionaryWord.query().order(
        -GlobalDictionaryWord.total_explanation_time).get()
    if word is None:
        return None
    return {"word": word.word, "seconds": word.total_explanation_time}


@producer("for_player_count")
def _games_by_player_count():
    return [{"player_count": row.player_count, "games": row.games}
            for row in GamesForPlayerCount.query().order(
                GamesForPlayerCount.player_count).fetch()]


@producer("daily_recent")
def _recent_days():
    """(date, games) for the last `_RECENT_DAYS` days, oldest first."""
    rows = DailyStatistics.query().order(-DailyStatistics.date).fetch(
        _RECENT_DAYS)
    return [(row.date.strftime("%Y-%m-%d"), row.games)
            for row in reversed(rows)]


@producer("per_game")
def _average_game():
    """What one game looks like, averaged over every day on record.

    Four sums over the whole history, which is the one thing here that cannot
    be answered from a tail -- and the reason this page used to read every
    DailyStatistics entity it had. As an aggregation it is a single round
    trip that never touches a row.
    """
    # One property per query, not one query summing four. Datastore serves a
    # multi-property aggregation out of a composite index the way it serves a
    # projection, and asking for four at once answers "400 no matching index
    # found"; a sum over a single property is served by the automatic index
    # that property already has. Four round trips instead of one, and no index
    # to build -- which also means no window after a deploy where this quietly
    # falls back to the scan it is here to replace.
    wanted = {"games": "games", "words": "words_used",
              "players": "players_participated",
              "seconds": "total_game_duration"}
    sums = {}
    for alias, prop in wanted.items():
        answer = _aggregate("DailyStatistics", [(alias, "sum", prop)])
        if answer is None:
            sums = None
            break
        sums[alias] = answer[alias]
    if sums is None:
        rows = DailyStatistics.query().fetch()
        sums = {"games": sum(row.games for row in rows),
                "words": sum(row.words_used for row in rows),
                "players": sum(row.players_participated for row in rows),
                "seconds": sum(row.total_game_duration for row in rows)}
    games = sums["games"]
    if not games:
        return None
    return {"words": sums["words"] / games,
            "players": sums["players"] / games,
            # Minutes were floored per day before being summed; over thousands
            # of days that is up to a day's worth of rounding, so the division
            # now happens once, at the end.
            "minutes": sums["seconds"] / 60.0 / games}


@router.get("/statistics/total_statistics", response_class=HTMLResponse)
def total_statistics(request: Request):
    total = TotalStatistics.get()
    by_hour = [0] * 24
    by_day = [0] * 7
    # 7x24 punchcard, same hour-of-week layout the old bubble chart used.
    # Slot 0 is the epoch hour, which fell on a Thursday, hence the +3 into a
    # week that starts on Monday.
    #
    # These hours are already each player's own wall clock, and must not be
    # shifted again here: stats._process_log adds the `time_zone_offset` the
    # client sent (v2) or `setup.meta['time.offset']` (v1) to the game's
    # start timestamp before update_total_statistics buckets it, falling back
    # to DEFAULT_OFFSET = UTC+4, which is what Moscow was when the app was
    # written. So a game at nine in the evening lands in the 21:00 slot
    # wherever it was played.
    punchcard = [[0] * 24 for _ in range(7)]
    for hour, games in enumerate(total.by_hour or []):
        by_hour[hour % 24] += games
        by_day[(hour // 24 + 3) % 7] += games
        punchcard[(hour // 24 + 3) % 7][hour % 24] += games
    punch_peak = max(max(row) for row in punchcard)

    daily_recent = cached("daily_recent")
    per_game = cached("per_game")
    longest = cached("longest_explanation")

    context = {
        "words_in_dictionary": cached("dict_word"),
        "used_words": cached("used_words"),
        "total_words": total.words_used,
        "total_games": total.games,
        "games_for_players": cached("for_player_count"),
        "daily_recent": daily_recent,
        "daily_recent_peak": max((games for _date, games in daily_recent),
                                 default=0),
        "by_hour": by_hour,
        "by_day": by_day,
        "punchcard": punchcard,
        "punch_peak": punch_peak,
        "longest_word": longest["word"] if longest else None,
        "longest_time": longest["seconds"] if longest else 0,
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
