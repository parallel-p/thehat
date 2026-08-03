# -*- coding: utf-8 -*-
"""Seed staging with the dictionary entries a replay needs.

Reads production (read-only) and writes staging. Refuses to write to `the-hat`.

    python -m scripts.seed_staging --logs tests/fixtures/prod_logs.jsonl \\
        --target the-hat-staging --reset-ratings

``--reset-ratings`` seeds every word at the factory defaults (E=50, D=50/3,
counters zeroed) instead of copying production's accumulated values. That is
what makes an end-to-end replay checkable: the expected final state can then be
computed independently by running the same logs through the python27 reference
from the same starting point.
"""

import argparse
import json
import logging
import os
import sys

logger = logging.getLogger(__name__)

BATCH = 400


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs", required=True)
    parser.add_argument("--source", default="the-hat")
    parser.add_argument("--target", default="the-hat-staging")
    parser.add_argument("--reset-ratings", action="store_true")
    parser.add_argument("--reset-state", action="store_true",
                        help="also delete the game logs and aggregate statistics "
                             "so a replay starts from a clean slate")
    parser.add_argument("--dictionary-key", default=None,
                        help="Dictionary(id=lang).gcs_key to set, e.g. 1564137725")
    parser.add_argument("--lang", default="ru")
    args = parser.parse_args()

    if args.target == "the-hat":
        parser.error("refusing to write to production; see MIGRATION_PLAN.md §8")

    from google.cloud import ndb

    from app.models import Dictionary, GlobalDictionaryWord
    from scripts.build_word_table import words_in_log
    from scripts.gcloud_auth import ndb_client

    wanted = set()
    with open(args.logs, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                wanted.update(words_in_log(json.loads(line)["json"]))
    ordered = sorted({w.lower() for w in wanted})
    logger.info("%d distinct words referenced", len(ordered))

    os.environ["GOOGLE_CLOUD_PROJECT"] = args.source
    source_client = ndb_client(args.source)
    found = {}
    with source_client.context(cache_policy=lambda key: False):
        for start in range(0, len(ordered), BATCH):
            chunk = ordered[start:start + BATCH]
            for word, entity in zip(chunk, ndb.get_multi(
                    [ndb.Key(GlobalDictionaryWord, w) for w in chunk])):
                if entity is not None:
                    found[word] = entity.lang or "ru"
    logger.info("%d of them exist in the production dictionary", len(found))

    os.environ["GOOGLE_CLOUD_PROJECT"] = args.target
    target_client = ndb_client(args.target)
    written = 0
    with target_client.context():
        if args.reset_state:
            for kind in ("GameLog", "TotalStatistics", "DailyStatistics",
                         "GamesForPlayerCount", "GameLength", "UnknownWord"):
                stale = ndb.Query(kind=kind).fetch(keys_only=True)
                if stale:
                    for chunk in range(0, len(stale), 400):
                        ndb.delete_multi(stale[chunk:chunk + 400])
                    logger.info("deleted %d %s entities", len(stale), kind)
        items = sorted(found.items())
        for start in range(0, len(items), BATCH):
            chunk = items[start:start + BATCH]
            entities = []
            for word, lang in chunk:
                if args.reset_ratings:
                    entities.append(GlobalDictionaryWord(
                        id=word, word=word, E=50.0, D=50.0 / 3, tags="",
                        lang=lang, used_times=0, guessed_times=0, failed_times=0,
                        total_explanation_time=0, counts_by_expl_time=[],
                        used_games=[]))
                else:
                    entities.append(GlobalDictionaryWord(
                        id=word, word=word, tags="", lang=lang))
            ndb.put_multi(entities)
            written += len(entities)
            logger.info("wrote %d/%d", written, len(items))

        if args.dictionary_key:
            Dictionary(id=args.lang, gcs_key=args.dictionary_key).put()
            logger.info("Dictionary(%s).gcs_key = %s", args.lang, args.dictionary_key)

    logger.info("seeded %s with %d words", args.target, written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
