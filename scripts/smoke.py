# -*- coding: utf-8 -*-
"""Smoke every API contract against a deployed instance.

    python -m scripts.smoke --target https://the-hat-staging.uc.r.appspot.com
    python -m scripts.smoke --target https://py3-dot-the-hat.appspot.com --read-only

Requests are sent with the User-Agents of the two live client generations, so
anything User-Agent dependent shows up here.

``--read-only`` runs only the GET checks. That is the mode for production
(MIGRATION_PLAN.md §8: no test writes to production, ever); the write paths must
already have been proven on staging.
"""

import argparse
import json
import logging
import sys
import urllib.error
import urllib.request
import uuid

logger = logging.getLogger(__name__)

DART_UA = "Dart/3.4 (dart:io)"
JAVA_UA = "Apache-HttpClient/UNAVAILABLE (java 1.4)"


class Smoke:
    def __init__(self, target):
        self.target = target.rstrip("/")
        self.failures = []
        self.checks = 0

    def request(self, method, path, body=None, headers=None):
        request = urllib.request.Request(
            self.target + path, data=body, method=method,
            headers=headers or {})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                # HTTPMessage, not dict: header lookup must stay case-insensitive,
                # and the app sends lowercase names.
                return response.status, response.headers, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.headers, error.read()

    def check(self, name, condition, detail=""):
        self.checks += 1
        if condition:
            logger.info("ok    %s", name)
        else:
            logger.error("FAIL  %s %s", name, detail)
            self.failures.append(name)

    # -- contracts ---------------------------------------------------------

    def dictionaries(self):
        status, headers, body = self.request(
            "GET", "/api/v2/dictionaries", headers={"User-Agent": DART_UA})
        self.check("GET /api/v2/dictionaries 200", status == 200, status)
        self.check("dictionaries content-type",
                   headers.get("Content-Type") == "text/html; charset=utf-8",
                   headers.get("Content-Type"))
        self.check("dictionaries body is a JSON array",
                   isinstance(_maybe_json(body), list), body[:80])

    def dictionary(self):
        status, headers, body = self.request(
            "GET", "/api/v2/dictionary/ru", headers={"User-Agent": DART_UA})
        self.check("GET /api/v2/dictionary/ru 200", status == 200, status)
        etag = headers.get("ETag")
        self.check("dictionary sets an ETag", bool(etag), etag)
        self.check("dictionary body parses", isinstance(_maybe_json(body), list),
                   body[:80])

        bare_status, _, bare_body = self.request("GET", "/api/v2/dictionary")
        self.check("bare /api/v2/dictionary matches /ru",
                   bare_status == 200 and bare_body == body, bare_status)

        if etag:
            status, _, cached = self.request(
                "GET", "/api/v2/dictionary/ru",
                headers={"If-None-Match": etag, "User-Agent": DART_UA})
            self.check("If-None-Match returns 304", status == 304, status)
            self.check("304 has an empty body", cached == b"", cached[:40])

        status, _, _ = self.request("GET", "/api/v2/dictionary/zz")
        self.check("unknown language is 404", status == 404, status)

    def web(self):
        for path in ("/", "/landing", "/statistics/word_statistics",
                     "/statistics/total_statistics", "/robots.txt",
                     "/favicon.ico"):
            status, _, _ = self.request("GET", path)
            self.check("GET {} 200".format(path), status == 200, status)

        _, _, robots = self.request("GET", "/robots.txt")
        self.check("robots.txt blocks /statistics/",
                   b"Disallow: /statistics/" in robots, robots[:60])

        index_status, _, index_body = self.request("GET", "/")
        landing_status, _, landing_body = self.request("GET", "/landing")
        self.check("/ is byte-identical to /landing",
                   index_status == landing_status == 200 and
                   index_body == landing_body,
                   "{} vs {}".format(len(index_body), len(landing_body)))

    def dropped_routes(self):
        for method, path in (("GET", "/dev1/pregame/get_current_game"),
                             ("GET", "/api/settings/user/get/all"),
                             ("GET", "/dev1/streams"),
                             ("GET", "/news/list"),
                             ("GET", "/admin/global_dictionary/add_words"),
                             ("GET", "/dev1/get_results/g1"),
                             ("GET", "/images/d_plot"),
                             ("GET", "/cron/notifications/update")):
            status, _, _ = self.request(method, path)
            self.check("dropped {} {} -> 404".format(method, path),
                       status == 404, status)

    def internal_is_protected(self):
        status, _, _ = self.request(
            "POST", "/internal/add_game_to_statistic",
            body=b"game_key=nope",
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        self.check("/internal rejects external callers", status == 403, status)

    # -- write paths (staging only) ----------------------------------------

    def game_log_v2(self):
        payload = json.dumps({"version": "2.0", "attempts": [],
                              "smoke": str(uuid.uuid4())}).encode()
        status, _, body = self.request(
            "POST", "/api/v2/game/log", body=payload,
            headers={"Content-Type": "application/json", "User-Agent": DART_UA})
        self.check("POST /api/v2/game/log 202", status == 202, status)
        self.check("v2 upload has an empty body", body == b"", body[:40])

    def game_log_v1(self):
        game_id = "smoke-{}".format(uuid.uuid4())
        device = "smoke-device-{}".format(uuid.uuid4().hex[:8])
        payload = json.dumps({
            "setup": {"type": "hat", "meta": {"game.id": game_id},
                      "words": [], "players": []},
            "events": []}).encode()
        for attempt in (1, 2):
            status, _, body = self.request(
                "PUT", "/{}/game_log/{}".format(device, game_id), body=payload,
                headers={"Content-Type": "application/json",
                         "User-Agent": JAVA_UA})
            self.check("PUT game_log 201 (attempt {})".format(attempt),
                       status == 201, status)
            self.check("v1 upload has an empty body (attempt {})".format(attempt),
                       body == b"", body[:40])

    def udict(self):
        device = "smoke-udict-{}".format(uuid.uuid4().hex[:8])
        word = "смоук{}".format(uuid.uuid4().hex[:6])

        status, headers, body = self.request(
            "POST", "/{}/api/udict".format(device),
            body=_form({"json": json.dumps([{"word": word, "status": "ok"}])}),
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "User-Agent": JAVA_UA})
        self.check("POST udict 200", status == 200, status)
        self.check("POST udict returns a bare integer", body.strip().isdigit(), body[:40])
        version = int(body.strip()) if body.strip().isdigit() else 0

        # Trailing slash must not redirect: the Java client cannot follow one.
        slash_status, _, _ = self.request(
            "POST", "/{}/api/udict/".format(device),
            body=_form({"json": json.dumps([{"word": word + "b", "status": "ok"}])}),
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "User-Agent": JAVA_UA})
        self.check("POST udict/ is not redirected", slash_status == 200, slash_status)

        status, _, body = self.request(
            "GET", "/{}/api/udict".format(device),
            headers={"User-Agent": JAVA_UA})
        self.check("GET udict 200", status == 200, status)
        parsed = _maybe_json(body) or {}
        self.check("GET udict returns version + words",
                   set(parsed) == {"version", "words"}, body[:120])
        self.check("GET udict lists the posted word",
                   any(w.get("word") == word for w in parsed.get("words", [])),
                   body[:200])
        self.check("GET udict excludes owner",
                   all("owner" not in w for w in parsed.get("words", [])),
                   body[:200])

        status, _, body = self.request(
            "GET", "/{}/api/udict/since/{}".format(device, version + 1),
            headers={"User-Agent": JAVA_UA})
        since = _maybe_json(body) or {}
        self.check("GET udict/since filters by version",
                   status == 200 and
                   all(w.get("word") != word for w in since.get("words", [])),
                   body[:200])


def _form(fields):
    from urllib.parse import urlencode

    return urlencode(fields).encode("utf-8")


def _maybe_json(body):
    try:
        return json.loads(body)
    except ValueError:
        return None


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True)
    parser.add_argument("--read-only", action="store_true")
    args = parser.parse_args()

    if args.read_only is False and "the-hat.appspot.com" in args.target \
            and "py3-dot" not in args.target:
        parser.error("refusing to run write checks against production")

    smoke = Smoke(args.target)
    smoke.dictionaries()
    smoke.dictionary()
    smoke.web()
    smoke.dropped_routes()
    smoke.internal_is_protected()

    if not args.read_only:
        smoke.game_log_v2()
        smoke.game_log_v1()
        smoke.udict()

    logger.info("")
    logger.info("%d checks, %d failures", smoke.checks, len(smoke.failures))
    for name in smoke.failures:
        logger.error("  failed: %s", name)
    return 1 if smoke.failures else 0


if __name__ == "__main__":
    sys.exit(main())
