# -*- coding: utf-8 -*-
"""Internal endpoints, reachable only from Cloud Tasks.

The python27 app protected ``/internal/*`` with ``login: admin`` in app.yaml.
Without the bundled App Engine APIs that mechanism is gone, so the replacement
is the ``X-AppEngine-QueueName`` header: App Engine strips it from external
requests and sets it on requests it delivers from a task queue.
"""

import logging

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool

from google.cloud import ndb

from app import settings
from app.http import legacy_response
from app.stats import add_game_to_statistic

logger = logging.getLogger(__name__)

router = APIRouter()

QUEUE_HEADER = "X-AppEngine-QueueName"


def is_task_request(request):
    if request.headers.get(QUEUE_HEADER):
        return True
    # Off App Engine (local tests, staging replay scripts) there is no frontend
    # to strip the header, so requiring it would make the endpoint unusable.
    return not settings.ON_APPENGINE


@router.post("/internal/add_game_to_statistic")
async def add_game_to_statistic_endpoint(request: Request):
    if not is_task_request(request):
        logger.warning("rejecting /internal request without %s", QUEUE_HEADER)
        return legacy_response(b"", status_code=403)

    form = await request.form()
    game_key = form.get("game_key")
    if not game_key:
        return legacy_response(b"", status_code=400)

    result = await run_in_threadpool(_run, game_key)
    logger.info("add_game_to_statistic %s -> %s", game_key, result)
    return legacy_response(b"", status_code=200)


def _run(game_key):
    return add_game_to_statistic(ndb.Key(urlsafe=game_key))
