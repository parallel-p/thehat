# -*- coding: utf-8 -*-
"""FastAPI application for The Hat.

Everything dropped by the migration (pregame, settings sync, streams, complaints,
newsfeed, admin pages, remote_api, appstats, Channel API notifications, plots,
function statistics, game results, save_game, link-device) simply has no route
and falls through to a 404. MIGRATION_PLAN.md §5.9 requires that they 404 rather
than 500, which is what an unrouted path does here.
"""

import logging

from fastapi import FastAPI
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import api_v1_compat, api_v2, internal, web
from app.ndb_ctx import NDBMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="The Hat",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    # The legacy Java client cannot follow redirects reliably; every legacy
    # path spelling is registered explicitly instead.
    redirect_slashes=False,
)

# Route order matters: the v1 compat router owns `/{device_id}/...`, which would
# otherwise shadow single-segment prefixes, so it is registered last.
app.include_router(web.router)
app.include_router(api_v2.router)
app.include_router(internal.router)
app.include_router(api_v1_compat.router)

app.add_middleware(NDBMiddleware)


@app.exception_handler(StarletteHTTPException)
async def on_http_exception(request, exc):
    if exc.status_code >= 500:
        logger.error("%s %s -> %s", request.method, request.url.path, exc.status_code)
    return await http_exception_handler(request, exc)
