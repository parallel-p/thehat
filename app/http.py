"""Response helpers that reproduce webapp2's defaults.

The two shipped client generations were written against webapp2 responses, and
one of them (Apache-HttpClient on a Java 1.4-era TLS stack) cannot be updated or
tested. Keeping the content type and cache headers identical removes a whole
class of risk for free.
"""

from fastapi import Response

# webapp2's default for a response with no explicit content type.
WEBAPP2_CONTENT_TYPE = "text/html; charset=utf-8"
WEBAPP2_HEADERS = {"Cache-Control": "no-cache"}


def legacy_response(body, status_code=200, media_type=WEBAPP2_CONTENT_TYPE,
                    headers=None):
    merged = dict(WEBAPP2_HEADERS)
    if headers:
        merged.update(headers)
    if isinstance(body, str):
        body = body.encode("utf-8")
    return Response(content=body, status_code=status_code,
                    media_type=media_type, headers=merged)
