# -*- coding: utf-8 -*-
"""Add words to the global dictionary. Replaces the /admin/global_dictionary UI.

    python -m scripts.add_words --project the-hat-staging --file words/new.txt
    python -m scripts.add_words --project the-hat-staging --file - --dry-run
    python -m scripts.add_words --project the-hat-staging --ratings-file pred.jsonl

New words are created with the same seed rating the old
``TaskQueueAddWords`` handler used (E=50.0, D=50/3, tags=""). With
``--ratings-file`` (jsonl rows {"word", "E"}, e.g. from
``ml/word_difficulty/predict.py``) each word is seeded with its predicted E
instead; D stays at the not-yet-played default. Words already present are
left untouched -- their accumulated ratings must not be reset.

Run ``python -m app.dictionary_gen`` afterwards to publish a new blob.
"""

import argparse
import json
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


def read_ratings(path):
    """jsonl rows {"word", "E"} -> ordered {word: E}, last row wins."""
    ratings = {}
    with open(path, encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                row = json.loads(line)
                ratings[row["word"].strip()] = float(row["E"])
    return ratings


def main():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", help="one word per line, or -")
    source.add_argument("--ratings-file",
                        help='jsonl rows {"word", "E"}: seed each word with '
                             "its predicted E")
    parser.add_argument("--lang", default="ru")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    os.environ["GOOGLE_CLOUD_PROJECT"] = args.project

    from google.cloud import ndb

    from app.models import GlobalDictionaryWord
    from scripts.gcloud_auth import ndb_client

    if args.ratings_file:
        ratings = read_ratings(args.ratings_file)
        words = list(ratings)
    else:
        ratings = {}
        words = read_words(args.file)
    logger.info("%d candidate words", len(words))

    client = ndb_client(args.project)
    added = 0
    with client.context():
        for start in range(0, len(words), BATCH):
            chunk = words[start:start + BATCH]
            existing = ndb.get_multi([ndb.Key(GlobalDictionaryWord, w) for w in chunk])
            new = [w for w, found in zip(chunk, existing) if found is None]
            if not new:
                continue
            logger.info("adding %d words (batch %d)", len(new), start // BATCH)
            if args.dry_run:
                added += len(new)
                continue
            ndb.put_multi([
                GlobalDictionaryWord(id=w, word=w, E=ratings.get(w, 50.0),
                                     D=50.0 / 3, tags="", lang=args.lang)
                for w in new
            ])
            added += len(new)

    logger.info("%s %d new words", "would add" if args.dry_run else "added", added)
    return 0


if __name__ == "__main__":
    sys.exit(main())
