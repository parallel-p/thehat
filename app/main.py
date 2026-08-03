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

from app import api_v1_compat, api_v2, internal, settings, web
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


def _mount_static_for_local_dev():
    """Serve /assets, /tos and /static when there is no App Engine frontend.

    In production these paths never reach the app -- app.yaml's static handlers
    answer them first, off-instance. Locally there is no such frontend, so
    without this `make serve` renders every page unstyled.
    """
    import os

    from fastapi.staticfiles import StaticFiles

    from fastapi.responses import FileResponse

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    for url, directory in (("/assets", "assets"), ("/tos", "tos")):
        path = os.path.join(root, directory)
        if os.path.isdir(path):
            app.mount(url, StaticFiles(directory=path, html=True), name=url[1:])

    # The single-file static handlers from app.yaml, so local URLs match prod.
    single_files = {
        "/robots.txt": ("static/robots.txt", "text/plain"),
        "/favicon.ico": ("favicon.ico", "image/x-icon"),
        "/android/beta": ("templates/android_beta.html", "text/html"),
        "/android/new/beta": ("templates/android_new_beta.html", "text/html"),
    }
    for url, (relative, media_type) in single_files.items():
        path = os.path.join(root, relative)
        if not os.path.exists(path):
            continue
        app.get(url, include_in_schema=False)(
            lambda path=path, media_type=media_type:
            FileResponse(path, media_type=media_type))


if not settings.ON_APPENGINE:
    _mount_static_for_local_dev()


@app.exception_handler(StarletteHTTPException)
async def on_http_exception(request, exc):
    if exc.status_code >= 500:
        logger.error("%s %s -> %s", request.method, request.url.path, exc.status_code)
    return await http_exception_handler(request, exc)
