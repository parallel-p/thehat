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
CRON_HEADER = "X-Appengine-Cron"


def is_task_request(request):
    if request.headers.get(QUEUE_HEADER):
        return True
    # Off App Engine (local tests, staging replay scripts) there is no frontend
    # to strip the header, so requiring it would make the endpoint unusable.
    return not settings.ON_APPENGINE


def is_cron_request(request):
    """Same mechanism as the queue header: App Engine sets `X-Appengine-Cron`
    on requests it delivers from cron.yaml and strips it from external ones."""
    if request.headers.get(CRON_HEADER):
        return True
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


# GET, not POST: App Engine cron only ever issues GETs. It is a write, which
# is why it is in here behind the cron header rather than on a public path.
@router.get("/internal/refresh_statistics")
async def refresh_statistics(request: Request):
    """Recompute the statistics pages' cached numbers. Called daily by cron.

    Without this the numbers are still correct -- whichever visitor finds an
    empty cache computes them -- but that visitor waits several seconds for
    the privilege. Doing it on a schedule means nobody does.
    """
    if not is_cron_request(request):
        logger.warning("rejecting /internal request without %s", CRON_HEADER)
        return legacy_response(b"", status_code=403)

    from app.web import refresh_all

    result = await run_in_threadpool(refresh_all)
    return result
