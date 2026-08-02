# -*- coding: utf-8 -*-
"""API v2 -- the endpoints the current Flutter client uses.

Contracts 1-3 of MIGRATION_PLAN.md §5. The python27 app served these through
webapp2, whose default response content type is ``text/html; charset=utf-8``
with ``Cache-Control: no-cache``; both are reproduced so the shipped clients see
byte-identical responses.
"""

import json
import logging
import re

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool

from google.cloud import ndb

from app import tasks
from app.http import legacy_response
from app.models import Dictionary, GameLog, get_langs
from app.storage import read_dictionary_blob

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/v2/game/log")
async def upload_game_log_v2(request: Request):
    """Contract 1: accept a game log, respond 202 with an empty body.

    The body is stored verbatim and never validated -- exactly what
    ``GameLog2Handler`` did.
    """
    raw = await request.body()
    await run_in_threadpool(_store_log_v2, raw.decode("utf-8"))
    return legacy_response(b"", status_code=202)


# A client-chosen id may only ever name a GameLog. It arrives from the network,
# so it is length-capped and restricted to the characters a UUID needs; anything
# else is ignored rather than rejected, since a log is worth more than an id.
_GAME_ID_RE = re.compile(r"\A[A-Za-z0-9_-]{8,64}\Z")


def _client_game_id(body):
    try:
        value = json.loads(body).get("game_id")
    except (ValueError, AttributeError):
        return None
    if isinstance(value, str) and _GAME_ID_RE.match(value):
        return value
    return None


def _store_log_v2(body):
    """Store one log and schedule its rating pass.

    A log that names itself with `game_id` is keyed by that id, so a client
    that retries after an ambiguous failure overwrites its own entity instead
    of adding a second one. That matters because ratings are cumulative and
    never recomputed: a game counted twice moves every word in it twice, and
    nothing later puts it back. Logs with no id keep the old behaviour -- an
    auto id, and no way to tell a retry from a new game.
    """
    game_id = _client_game_id(body)
    if game_id is None:
        key = GameLog(json=body).put()
        tasks.enqueue_stats_task(key.urlsafe().decode("ascii"))
        return

    key = ndb.Key(GameLog, game_id)
    if key.get() is not None:
        # Already accepted. Not re-queued: the first task either has run or is
        # still to run, and either way it rates this game exactly once.
        logger.info("duplicate game log %s ignored", game_id)
        return
    GameLog(key=key, json=body).put()
    tasks.enqueue_stats_task(key.urlsafe().decode("ascii"))


@router.get("/api/v2/dictionary")
def get_dictionary_default(request: Request):
    return _serve_dictionary(request, "ru")


@router.get("/api/v2/dictionary/{lang}")
def get_dictionary(request: Request, lang: str):
    return _serve_dictionary(request, lang)


def _serve_dictionary(request, lang):
    """Contract 2: stream the generated dictionary blob for ``lang``."""
    dictionary = ndb.Key(Dictionary, lang).get()
    if not dictionary:
        return legacy_response(b"", status_code=404)
    key = dictionary.gcs_key

    # Note: the python27 handler returned before setting the ETag on a 304, so
    # a 304 carries no ETag header. Reproduced here.
    if etag_matches(request.headers.get("if-none-match"), key):
        return legacy_response(b"", status_code=304)

    data = read_dictionary_blob(key)
    # The blob is rebuilt by a cron, not per request, and the ETag already makes
    # a stale read safe -- so let a client hold it for an hour and revalidate in
    # the background rather than blocking a game on a conditional request.
    return legacy_response(data, headers={
        "ETag": '"{}"'.format(key),
        "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
    })


@router.get("/api/v2/word_seconds")
async def word_seconds():
    """What a difficulty rating is worth on a stopwatch.

    The rating is dimensionless by construction (see web._seconds_curve), so
    the app at /play cannot turn a difficulty setting into "about nine seconds
    a word" on its own. It asks here instead of carrying a copy of the numbers,
    which would quietly go stale as the corpus grows; the answer is a reading
    at every difficulty from 0 to 100, changes about as often as the
    dictionary, and the app keeps the last one it received so that an evening
    with no signal still has one.

    [{"d": 0..100, "avg": seconds per attempt, "count": words behind it}]
    """
    from app import web            # local: web imports nothing from here

    rows = await run_in_threadpool(web.word_seconds)
    return legacy_response(json.dumps(rows), headers={
        "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
    })


@router.get("/api/v2/dictionaries")
def list_dictionaries():
    """Contract 3: the list of available languages, as a JSON array."""
    return legacy_response(json.dumps(get_langs()))


def etag_matches(header_value, key):
    """Mimic webob's ``key in request.if_none_match``."""
    if not header_value or key is None:
        return False
    for candidate in header_value.split(","):
        candidate = candidate.strip()
        if candidate == "*":
            return True
        if candidate.startswith("W/"):
            candidate = candidate[2:].strip()
        if candidate[:1] == '"' and candidate[-1:] == '"':
            candidate = candidate[1:-1]
        if candidate == key:
            return True
    return False
