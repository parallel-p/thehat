# -*- coding: utf-8 -*-
"""API v1 compatibility -- the legacy Java Android client.

Contracts 4-6 of MIGRATION_PLAN.md §5. Ten devices still speak this API from an
Apache-HttpClient/Java-1.4-era stack that cannot be updated or tested, so:

* no redirects (both the trailing-slash and no-slash spellings are registered),
* no HTTPS upgrade, no HSTS, no strict validation,
* unknown device ids are still auto-created on read.

Every other legacy route (results, save_game, complain, settings sync, pregame)
is intentionally gone and falls through to 404.
"""

import json
import logging

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool

from google.cloud import ndb

from app import tasks
from app.http import legacy_response
from app.models import (GameLog, UserDictionaryWord, get_device_and_user)

logger = logging.getLogger(__name__)

router = APIRouter()

DEVICE_HEADER = "TheHat-Device-Identity"


def resolve_device(request, device_id):
    """``AuthorizedAPIRequestHandler.dispatch``: URL id, else header, else 401."""
    device_id = device_id or request.headers.get(DEVICE_HEADER)
    if device_id is None:
        return None, None, legacy_response(
            b"", status_code=401, headers={"WWW-Authenticate": "device-id"})
    device_key, user_key = get_device_and_user(device_id)
    return device_key, user_key, None


# --------------------------------------------------------------------------
# Contract 4 -- game log upload
# --------------------------------------------------------------------------


@router.put("/{device_id}/game_log")
@router.put("/{device_id}/game_log/{game_id}")
async def upload_game_log_v1(request: Request, device_id: str, game_id: str = None):
    """Idempotent upload. Always answers 201, even for a duplicate.

    The game id comes from the *body* (``setup.meta["game.id"]``), never from
    the URL -- the URL component is ignored, exactly as in ``GameLogHandler``.
    """
    raw = await request.body()
    return await run_in_threadpool(_store_log_v1, request, device_id, raw)


def _store_log_v1(request, device_id, raw):
    _, _, error = resolve_device(request, device_id)
    if error is not None:
        return error

    body = raw.decode("utf-8")
    log_id = json.loads(body)['setup']['meta']['game.id']
    if ndb.Key(GameLog, log_id).get() is None:
        key = GameLog(json=body, id=log_id).put()
        tasks.enqueue_stats_task(key.urlsafe().decode("ascii"))
    return legacy_response(b"", status_code=201)


# --------------------------------------------------------------------------
# Contracts 5 and 6 -- user dictionary sync
# --------------------------------------------------------------------------


def _get_max_version(user_key):
    word = (UserDictionaryWord.query(user_key)
            .order(-UserDictionaryWord.version).get())
    return word.version if word else 0


@router.get("/{device_id}/api/udict")
@router.get("/{device_id}/api/udict/")
@router.get("/{device_id}/api/udict/since/{version}")
def get_user_dictionary(request: Request, device_id: str, version: str = "0"):
    """Contract 5: words changed since ``version``, plus the current version."""
    _, user_key, error = resolve_device(request, device_id)
    if error is not None:
        return error

    version_on_device = int(version)
    current_version = _get_max_version(user_key)
    diff = UserDictionaryWord.query(
        user_key, UserDictionaryWord.version > version_on_device)
    body = json.dumps({"version": current_version,
                       "words": [el.to_dict(exclude=('owner',)) for el in diff]})
    return legacy_response(body)


@router.post("/{device_id}/api/udict")
@router.post("/{device_id}/api/udict/")
@router.post("/{device_id}/api/udict/since/{version}")
async def post_user_dictionary(request: Request, device_id: str, version: str = "0"):
    """Contract 6: upsert the posted words, answer with the bare new version.

    Changes arrive as the form field ``json`` of an
    ``application/x-www-form-urlencoded`` body, and the response body is the
    version integer with no JSON wrapper.
    """
    form = await request.form()
    payload = form.get("json") or ""
    return await run_in_threadpool(_apply_user_dictionary, request, device_id, payload)


def _apply_user_dictionary(request, device_id, payload):
    device_key, user_key, error = resolve_device(request, device_id)
    if error is not None:
        return error

    changes = json.loads(payload)
    new_version = _get_max_version(user_key) + 1
    for el in changes:
        current_word = (UserDictionaryWord.query(
            user_key, UserDictionaryWord.word == el["word"]).get() or
            UserDictionaryWord(owner=device_key))
        current_word.populate(version=new_version, **el)
        current_word.put()
    return legacy_response(str(new_version))
