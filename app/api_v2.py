# -*- coding: utf-8 -*-
"""API v2 -- the endpoints the current Flutter client uses.

Contracts 1-3 of MIGRATION_PLAN.md §5. The python27 app served these through
webapp2, whose default response content type is ``text/html; charset=utf-8``
with ``Cache-Control: no-cache``; both are reproduced so the shipped clients see
byte-identical responses.
"""

import json
import logging

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


def _store_log_v2(body):
    key = GameLog(json=body).put()
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
    return legacy_response(data, headers={"ETag": '"{}"'.format(key)})


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
