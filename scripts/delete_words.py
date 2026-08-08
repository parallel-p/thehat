# -*- coding: utf-8 -*-
"""Soft-delete words from the global dictionary.

    python -m scripts.delete_words --project the-hat-staging --file bad.txt
    python -m scripts.delete_words --project the-hat-staging --file - --dry-run

Sets ``deleted=True`` on each listed word; ratings and counters stay intact,
so a mistake is undone by flipping the flag back. Words that are absent or
already deleted are reported and skipped.

Run ``python -m app.dictionary_gen`` afterwards to publish a new blob.
"""

import argparse
import logging
import os
import sys

logger = logging.getLogger(__name__)

BATCH = 200


def read_words(path):
    stream = sys.stdin if path == "-" else open(path, encoding="utf-8")
    try:
        seen = []
        for line in stream:
            word = line.strip()
            if word and not word.startswith("#"):
                seen.append(word)
    finally:
        if stream is not sys.stdin:
            stream.close()
    # Preserve input order, drop duplicates.
    return list(dict.fromkeys(seen))


def main():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--file", required=True, help="one word per line, or -")
    parser.add_argument("--lang", default="ru")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    os.environ["GOOGLE_CLOUD_PROJECT"] = args.project

    from google.cloud import ndb

    from app.models import GlobalDictionaryWord
    from scripts.gcloud_auth import ndb_client

    words = read_words(args.file)
    logger.info("%d candidate words", len(words))

    client = ndb_client(args.project)
    marked = 0
    absent = []
    already = []
    with client.context():
        for start in range(0, len(words), BATCH):
            chunk = words[start:start + BATCH]
            existing = ndb.get_multi([ndb.Key(GlobalDictionaryWord, w) for w in chunk])
            to_mark = []
            for word, entity in zip(chunk, existing):
                if entity is None:
                    absent.append(word)
                elif entity.deleted:
                    already.append(word)
                elif entity.lang != args.lang:
                    logger.warning("skipping %s: lang=%s", word, entity.lang)
                else:
                    entity.deleted = True
                    to_mark.append(entity)
            if not to_mark:
                continue
            logger.info("marking %d words deleted (batch %d)",
                        len(to_mark), start // BATCH)
            if args.dry_run:
                marked += len(to_mark)
                continue
            ndb.put_multi(to_mark)
            marked += len(to_mark)

    verb = "would mark" if args.dry_run else "marked"
    logger.info("%s %d words deleted; %d absent, %d already deleted",
                verb, marked, len(absent), len(already))
    if absent:
        logger.info("absent: %s", " ".join(absent))
    if already:
        logger.info("already deleted: %s", " ".join(already))
    return 0


if __name__ == "__main__":
    sys.exit(main())
