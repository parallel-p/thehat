"""One ``google-cloud-ndb`` context per HTTP request.

``Context`` is stored in a :mod:`contextvars` variable, so entering it in an
ASGI middleware makes it visible to the route handler -- including sync (``def``)
handlers, which Starlette runs in a threadpool with a copy of the current
context.
"""

import functools

from google.cloud import ndb
from google.cloud.ndb import context as context_module

from app import settings
from app.gcp_auth import credentials

_client = None


def client():
    global _client
    if _client is None:
        _client = ndb.Client(project=settings.PROJECT_ID,
                             credentials=credentials())
    return _client


def with_context(func):
    """Wrap a plain function so it runs inside a fresh ndb context.

    Used by scripts and by tests; request handlers get their context from
    :class:`NDBMiddleware` instead.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with client().context():
            return func(*args, **kwargs)

    return wrapper


class NDBMiddleware:
    """Pure-ASGI middleware; deliberately not ``BaseHTTPMiddleware``.

    ``BaseHTTPMiddleware`` runs the downstream app in a separate task, which
    would put the ndb context in a context the handler cannot see.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or context_module.get_context(False) is not None:
            # Under the server every request task starts from a context-free
            # root, so the second condition only fires in tests, where the test
            # itself owns the context.
            await self.app(scope, receive, send)
            return
        with client().context():
            await self.app(scope, receive, send)
