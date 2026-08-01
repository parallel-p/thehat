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
                        GlobalDictionaryWord, TotalStatistics)

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


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    """The landing page. `/landing` serves the same file as a static handler."""
    return templates.TemplateResponse(request, "landing.html")


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
    return templates.TemplateResponse(request, "word_statistics.html", context)


@router.get("/statistics/total_statistics", response_class=HTMLResponse)
def total_statistics(request: Request):
    total = TotalStatistics.get()
    by_hour = [0] * 24
    by_day = [0] * 7
    for hour, games in enumerate(total.by_hour or []):
        by_hour[hour % 24] += games
        by_day[(hour // 24 + 3) % 7] += games

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
        "daily": cached(
            "daily",
            lambda: [(el.date.strftime("%Y-%m-%d"), el.games, el.words_used,
                      el.players_participated, el.total_game_duration // 60)
                     for el in DailyStatistics.query().order(
                         DailyStatistics.date).fetch()]),
        "by_hour": by_hour,
        "by_day": by_day,
    }
    return templates.TemplateResponse(request, "total_statistics.html", context)


@router.get("/_ah/warmup", include_in_schema=False)
def warmup():
    return {"status": "ok"}


@router.get("/healthz", include_in_schema=False)
def healthz():
    """Liveness probe used by WP1's deploy smoke test."""
    return {"status": "ok"}
