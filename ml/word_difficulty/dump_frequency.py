# -*- coding: utf-8 -*-
"""Dump the WordFrequency table (corpus uses per million) from production.

Read-only. Writes prod_frequency.jsonl next to this file.

    python ml/word_difficulty/dump_frequency.py [--project the-hat]
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
    parser.add_argument("--out", default=os.path.join(HERE, "prod_frequency.jsonl"))
    args = parser.parse_args()

    os.environ["GOOGLE_CLOUD_PROJECT"] = args.project
    os.environ.pop("DATASTORE_EMULATOR_HOST", None)

    from scripts.gcloud_auth import ndb_client
    from app.models import WordFrequency

    client = ndb_client(args.project)
    count = 0
    with client.context():
        with open(args.out, "w", encoding="utf-8") as handle:
            for entity in WordFrequency.query():
                handle.write(json.dumps(
                    {"key": entity.key.id(), "word": entity.word,
                     "frequency": entity.frequency},
                    ensure_ascii=False) + "\n")
                count += 1
                if count % 5000 == 0:
                    print(f"...{count}", flush=True)
    print(f"done: {count} -> {args.out}")


if __name__ == "__main__":
    main()
