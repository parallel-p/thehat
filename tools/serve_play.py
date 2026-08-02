"""Serve /play locally the way app.yaml serves it, against a saved dictionary.

    make play            # then open http://localhost:8901/play

Development only -- the real routing is in app.yaml and the real dictionary
comes from the datastore. This exists because the app cannot be looked at
without /play resolving to one file, /play/* to its shell, and
/api/v2/dictionary/ru to something with words in it.

Uploaded game logs are printed and written to /tmp/last_game_log.json, which
is the cheapest way to see exactly what the server would receive.
"""
import http.server
import json
import os
import socketserver
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT = os.path.join(ROOT, ".dictionary-cache.json")
DICT_URL = "https://the-hat-staging.uc.r.appspot.com/api/v2/dictionary/ru"
PORT = 8901


class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = path.split("?", 1)[0].split("#", 1)[0]
        if path == "/play" or path == "/play/":
            return os.path.join(ROOT, "static/play/index.html")
        if path.startswith("/play/"):
            return os.path.join(ROOT, "static/play", path[len("/play/"):])
        return os.path.join(ROOT, path.lstrip("/"))

    def end_headers(self):
        if self.path.startswith("/play/sw.js"):
            self.send_header("Service-Worker-Allowed", "/play")
        super().end_headers()

    def do_GET(self):
        if self.path.startswith("/slow"):
            # Holds the load event open so a headless screenshot happens after
            # the page's async work, not at parse time.
            import time
            time.sleep(float(self.path.split("=")[-1]) if "=" in self.path else 4)
            self.send_response(200)
            self.send_header("Content-Type", "image/gif")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.path.startswith("/api/v2/word_seconds"):
            # The real one is a reading at every difficulty, computed from the
            # statistics pipeline; locally there is no datastore, so serve a
            # curve of the same shape.
            curve = []
            for d in range(20, 86):
                # Roughly what production reports: a few seconds at the easy
                # end, growing steeply past the middle.
                curve.append({"d": d, "avg": round(1.15 * pow(1.0425, d), 2),
                              "count": 120})
            body = json.dumps(curve).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith("/api/v2/dictionary"):
            with open(DICT, "rb") as handle:
                body = handle.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("ETag", '"local"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def do_POST(self):
        length = int(self.headers.get("content-length", 0))
        raw = self.rfile.read(length)
        try:
            log = json.loads(raw)
            print("LOG game_id=%s attempts=%d" % (
                log.get("game_id"), len(log.get("attempts", []))))
            with open("/tmp/last_game_log.json", "wb") as handle:
                handle.write(raw)
        except Exception as exc:      # noqa: BLE001 -- dev tool
            print("bad log:", exc)
        self.send_response(202)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args):
        pass


class Server(socketserver.ThreadingTCPServer):
    # Threaded on purpose: /slow blocks its own request, and single-threaded
    # that blocks the module fetches too -- which looks exactly like the app
    # hanging, and is a fine way to spend an hour misdiagnosing.
    allow_reuse_address = True
    daemon_threads = True


if not os.path.exists(DICT):
    print("fetching a dictionary to play with ...")
    with urllib.request.urlopen(DICT_URL) as response, open(DICT, "wb") as out:
        out.write(response.read())

with Server(("", PORT), Handler) as httpd:
    print("http://localhost:%d/play" % PORT)
    httpd.serve_forever()
