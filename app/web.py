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


def _word_shape():
    """One projection pass over the dictionary: (word, E, D, used, failed).

    A projection stays index-only, so the heavyweight `used_games` lists are
    never loaded. Words never attempted are dropped. Needs the composite
    index on (E, D, used_times, failed_times) in index.yaml.
    """
    query = GlobalDictionaryWord.query(
        projection=[GlobalDictionaryWord.E, GlobalDictionaryWord.D,
                    GlobalDictionaryWord.used_times,
                    GlobalDictionaryWord.failed_times])
    rows = [(entity.key.id(), entity.E, entity.D,
             entity.used_times, entity.failed_times)
            for entity in query.fetch()]
    return [row for row in rows if row[3]]


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


def _word_analytics():
    """The analytical stats the old site drew as matplotlib PNGs, plus the
    error-prone-words table, all from one projection pass.

    The stored `danger` property keeps the py27 floor-division bug and is
    ~always 0, so the error rate is computed honestly here instead of
    ordering by that property the way the legacy page did.
    """
    try:
        shape = _word_shape()
    except Exception:  # noqa: BLE001 -- e.g. the composite index still
        # building right after a deploy; the page must render without the
        # analytics rather than 500. The empty result ages out with the cache.
        logger.exception("word-shape projection unavailable; hiding analytics")
        shape = []

    by_length = {}
    for word, e, _d, _used, _failed in shape:
        length = min(len(word), 13)
        by_length.setdefault(length, []).append(e)
    length_rows = [
        {"label": "13+" if length == 13 else str(length),
         "avg": sum(es) / len(es), "count": len(es)}
        for length, es in sorted(by_length.items()) if len(es) >= 5]

    d_by_games = {}
    for _word, _e, d, used, _failed in shape:
        bucket = min(used, 8)
        d_by_games.setdefault(bucket, []).append(d)
    d_rows = [
        {"label": "8+" if bucket == 8 else str(bucket),
         "avg": sum(ds) / len(ds), "count": len(ds)}
        for bucket, ds in sorted(d_by_games.items())]

    frequencies = _frequency_map()
    freq_groups = [[] for _ in _FREQ_BUCKETS]
    for word, e, _d, _used, _failed in shape:
        frequency = frequencies.get(word)
        if frequency is None:
            continue
        for index, (low, high, _label) in enumerate(_FREQ_BUCKETS):
            if low <= frequency < high:
                freq_groups[index].append(e)
                break
    freq_rows = [
        {"label": label, "avg": sum(es) / len(es), "count": len(es)}
        for (low, high, label), es in zip(_FREQ_BUCKETS, freq_groups) if es]

    danger = sorted(
        ({"word": word, "E": e, "share": 100.0 * failed / used}
         for word, e, _d, used, failed in shape if used >= 10 and failed),
        key=lambda row: -row["share"])[:10]

    return {"by_length": length_rows, "d_by_games": d_rows,
            "by_freq": freq_rows, "danger_top": danger}


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
        context["top"] = cached(
            "words_top",
            lambda: GlobalDictionaryWord.query().order(
                -GlobalDictionaryWord.E).fetch(limit=10))
        context["bottom"] = cached(
            "words_bottom",
            lambda: GlobalDictionaryWord.query().order(
                GlobalDictionaryWord.E).fetch(limit=10))
        count = cached(
            "used_words_count",
            lambda: GlobalDictionaryWord.query(
                GlobalDictionaryWord.used_times > 0).count())
        if count >= 10:
            context["rand"] = GlobalDictionaryWord.query(
                GlobalDictionaryWord.used_times > 0).fetch(
                    limit=10, offset=random.randint(0, count - 10))
        context["danger_top"] = cached(
            "word_analytics", _word_analytics)["danger_top"]
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
        "analytics": cached("word_analytics", _word_analytics),
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
