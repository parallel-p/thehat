# -*- coding: utf-8 -*-
"""Read-only export of GameLog payloads, for building test fixtures.

Production Datastore is read-only for this migration (MIGRATION_PLAN.md §8);
this script only ever runs queries.

    python -m scripts.export_prod_logs --project the-hat --limit 200 \\
        --out tests/fixtures/game_logs.jsonl
"""

import argparse
import json
import logging
import os
import sys

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="the-hat")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--out", required=True)
    parser.add_argument("--ignored", action="store_true",
                        help="export only logs the pipeline rejected")
    parser.add_argument("--recent", action="store_true",
                        help="most recently played first (GameLog.time desc)")
    parser.add_argument("--page-size", type=int, default=100)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    os.environ["GOOGLE_CLOUD_PROJECT"] = args.project
    os.environ.pop("DATASTORE_EMULATOR_HOST", None)

    from app.models import GameLog
    from scripts.gcloud_auth import ndb_client

    client = ndb_client(args.project)
    exported = 0
    with client.context(cache_policy=lambda key: False):
        query = (GameLog.query(GameLog.ignored == True)  # noqa: E712
                 if args.ignored else GameLog.query())
        if args.recent:
            # `time` is only set once a game has been processed, so this also
            # filters out logs the pipeline never got to.
            query = query.order(-GameLog.time)
        with open(args.out, "w", encoding="utf-8") as handle:
            cursor = None
            while exported < args.limit:
                page, cursor, more = query.fetch_page(
                    min(args.page_size, args.limit - exported),
                    start_cursor=cursor)
                for log in page:
                    handle.write(json.dumps({
                        "id": log.key.id(),
                        "urlsafe": log.key.urlsafe().decode("ascii"),
                        "ignored": bool(log.ignored),
                        "reason": log.reason,
                        "time": log.time.isoformat() if log.time else None,
                        "json": log.json,
                    }, ensure_ascii=False) + "\n")
                    exported += 1
                if not more or not page:
                    break
    logger.info("exported %d logs to %s", exported, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
