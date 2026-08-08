# -*- coding: utf-8 -*-
"""Dump the full production GlobalDictionaryWord table to JSONL.

Read-only with respect to production. Writes prod_dictionary.jsonl next to
this file, one line per entity.

    python ml/word_difficulty/dump_dictionary.py [--project the-hat]
"""

import argparse
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="the-hat")
    parser.add_argument("--out", default=os.path.join(HERE, "prod_dictionary.jsonl"))
    args = parser.parse_args()

    os.environ["GOOGLE_CLOUD_PROJECT"] = args.project
    os.environ.pop("DATASTORE_EMULATOR_HOST", None)

    from scripts.gcloud_auth import ndb_client
    from app.models import GlobalDictionaryWord

    client = ndb_client(args.project)
    count = 0
    with client.context():
        with open(args.out, "w", encoding="utf-8") as handle:
            for entity in GlobalDictionaryWord.query():
                row = {
                    "key": entity.key.id(),
                    "word": entity.word,
                    "E": entity.E,
                    "D": entity.D,
                    "used_times": entity.used_times,
                    "guessed_times": entity.guessed_times,
                    "failed_times": entity.failed_times,
                    "lang": entity.lang,
                    "deleted": entity.deleted,
                    "tags": entity.tags,
                }
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                count += 1
                if count % 2000 == 0:
                    print(f"...{count}", flush=True)
    print(f"done: {count} entities -> {args.out}")


if __name__ == "__main__":
    main()
