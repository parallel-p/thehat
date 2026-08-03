# -*- coding: utf-8 -*-
"""WP5: replay real game-log payloads against staging and compare with production.

Never point this at production -- it writes. The default target is staging and
the script refuses `the-hat` unless `--i-know-this-writes` is passed, which
nothing in the migration plan ever needs.

    python -m scripts.replay_logs --logs tests/fixtures/prod_logs.jsonl \\
        --target https://the-hat-staging.uc.r.appspot.com \\
        --project the-hat-staging --compare-with the-hat

Two phases:

1. upload each payload through the real HTTP contract (v2 logs via
   ``POST /api/v2/game/log``, v1 logs via ``PUT /<device>/game_log``) and run
   the statistics task synchronously, so a failure is attributable to one log;
2. compare the resulting ``GlobalDictionaryWord`` E/D against production for
   every word those games touched, and report the largest divergence.
"""

import argparse
import json
import logging
import os
import sys
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

REPLAY_DEVICE = "replay-harness"


def post(url, body, headers, method="POST"):
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def upload(target, entry):
    payload = entry["json"].encode("utf-8")
    log = json.loads(entry["json"])
    if log.get("version") == "2.0":
        return post("{}/api/v2/game/log".format(target), payload,
                    {"Content-Type": "application/json",
                     "User-Agent": "Dart/3.4 (dart:io)"})
    return post("{}/{}/game_log".format(target, REPLAY_DEVICE), payload,
                {"Content-Type": "application/json",
                 "User-Agent": "Apache-HttpClient/UNAVAILABLE (java 1.4)"},
                method="PUT")


def replay(args):
    """Upload every payload through the real HTTP contract.

    With ``--sequential`` each game is fully processed before the next is
    uploaded. Cloud Tasks does not promise FIFO delivery even at concurrency 1,
    and the rating maths is path-dependent, so any comparison against an
    ordered reference run has to force the order here.
    """
    uploaded, failures = 0, []
    counter = _GameCounter(args) if args.sequential else None

    with open(args.logs, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            entry = json.loads(line)
            status, body = upload(args.target, entry)
            if status not in (201, 202):
                failures.append((entry["id"], status, body[:200]))
                logger.error("upload of %s failed: %s", entry["id"], status)
                continue
            uploaded += 1
            if counter is not None and not counter.wait_for(uploaded, entry["id"]):
                failures.append((entry["id"], "timeout", b""))
            elif uploaded % 50 == 0:
                logger.info("uploaded %d", uploaded)
    logger.info("uploaded %d logs, %d failures", uploaded, len(failures))
    return failures


class _GameCounter:
    """Blocks until TotalStatistics.games reaches a target."""

    def __init__(self, args):
        from scripts.gcloud_auth import ndb_client

        self.client = ndb_client(args.project)
        self.timeout = args.timeout

    def games(self):
        from app.models import TotalStatistics

        with self.client.context(cache_policy=lambda key: False):
            return TotalStatistics.get().games

    def wait_for(self, target, game_id):
        import time

        deadline = time.time() + self.timeout
        while time.time() < deadline:
            if self.games() >= target:
                return True
            time.sleep(2)
        logger.error("timed out waiting for %s to be processed", game_id)
        return False


def words_in(entry):
    from scripts.build_word_table import words_in_log

    return words_in_log(entry["json"])


def compare(args):
    """Compare E/D per word between the replay target and production."""
    from app.models import GlobalDictionaryWord
    from scripts.gcloud_auth import ndb_client

    wanted = set()
    with open(args.logs, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                wanted.update(words_in(json.loads(line)))

    def snapshot(project):
        client = ndb_client(project)
        values = {}
        with client.context(cache_policy=lambda key: False):
            for word in sorted(wanted):
                entity = GlobalDictionaryWord.get(word)
                if entity is not None:
                    values[word.lower()] = (entity.E, entity.D, entity.used_times)
        return values

    replayed = snapshot(args.project)
    production = snapshot(args.compare_with)

    common = sorted(set(replayed) & set(production))
    worst = []
    for word in common:
        got, want = replayed[word], production[word]
        worst.append((max(abs(got[0] - want[0]), abs(got[1] - want[1])), word, got, want))
    worst.sort(reverse=True)

    logger.info("%d words compared (of %d referenced)", len(common), len(wanted))
    for delta, word, got, want in worst[:20]:
        logger.info("  %-24s delta=%.6f staging=%s prod=%s", word, delta, got, want)
    if worst:
        logger.info("largest divergence: %.9f", worst[0][0])
    return worst


def wait_for_queue(args):
    """Block until the statistics queue has processed every accepted game."""
    import time

    from app.models import TotalStatistics
    from scripts.gcloud_auth import ndb_client

    client = ndb_client(args.project)
    deadline = time.time() + args.timeout
    seen = -1
    while time.time() < deadline:
        with client.context(cache_policy=lambda key: False):
            seen = TotalStatistics.get().games
        if seen >= args.expect_games:
            logger.info("queue drained: %d games processed", seen)
            return True
        logger.info("waiting: %d/%d games processed", seen, args.expect_games)
        time.sleep(10)
    logger.error("timed out at %d/%d games", seen, args.expect_games)
    return False


def verify_final(args):
    """Compare the target's word state against the python27 prediction."""
    from google.cloud import ndb

    from app.models import GlobalDictionaryWord
    from scripts.gcloud_auth import ndb_client

    with open(args.verify_final, encoding="utf-8") as handle:
        expected = json.load(handle)

    client = ndb_client(args.project)
    checked, touched, mismatches, worst = 0, 0, [], 0.0
    keys = sorted(expected)
    with client.context(cache_policy=lambda key: False):
        for start in range(0, len(keys), 400):
            chunk = keys[start:start + 400]
            entities = ndb.get_multi(
                [ndb.Key(GlobalDictionaryWord, w.lower()) for w in chunk])
            for word, entity in zip(chunk, entities):
                want = expected[word]
                if entity is None:
                    continue
                checked += 1
                if want["used_times"]:
                    touched += 1
                delta = max(abs(entity.E - want["E"]), abs(entity.D - want["D"]))
                worst = max(worst, delta)
                counters_ok = (
                    entity.used_times == want["used_times"] and
                    entity.guessed_times == want["guessed_times"] and
                    entity.failed_times == want["failed_times"] and
                    entity.total_explanation_time == want["total_explanation_time"])
                if delta > 1e-9 or not counters_ok:
                    mismatches.append((word, delta, entity.E, want["E"],
                                       entity.used_times, want["used_times"]))

    logger.info("compared %d words (%d actually rated by the replay)",
                checked, touched)
    logger.info("largest E/D divergence: %.12g", worst)
    for row in mismatches[:20]:
        logger.error("  mismatch %s delta=%.9g got_E=%s want_E=%s got_used=%s want_used=%s",
                     *row)
    if mismatches:
        logger.error("%d words diverge from the python27 prediction", len(mismatches))
        return False
    if not touched:
        logger.error("no word was rated; the replay proved nothing")
        return False
    logger.info("end-to-end state matches the python27 reference exactly")
    return True


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs", required=True)
    parser.add_argument("--target", default="https://the-hat-staging.uc.r.appspot.com")
    parser.add_argument("--project", default="the-hat-staging")
    parser.add_argument("--compare-with", default=None,
                        help="project to diff word ratings against, e.g. the-hat")
    parser.add_argument("--skip-upload", action="store_true")
    parser.add_argument("--sequential", action="store_true",
                        help="wait for each game to be processed before "
                             "uploading the next, so the processing order is "
                             "the file order")
    parser.add_argument("--i-know-this-writes", action="store_true")
    parser.add_argument("--expect-games", type=int,
                        help="number of logs that should be accepted; the replay "
                             "waits until TotalStatistics.games reaches it")
    parser.add_argument("--verify-final", metavar="PATH",
                        help="JSON word state produced by run_reference.py "
                             "--accumulate; compared against the target after "
                             "the queue drains")
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()

    if args.project == "the-hat" and not args.i_know_this_writes:
        parser.error("refusing to replay into production; see MIGRATION_PLAN.md §8")

    os.environ["GOOGLE_CLOUD_PROJECT"] = args.project

    failures = [] if args.skip_upload else replay(args)
    if args.expect_games and not wait_for_queue(args):
        return 1
    if args.verify_final and not verify_final(args):
        return 1
    if args.compare_with:
        compare(args)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
