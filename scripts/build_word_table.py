# -*- coding: utf-8 -*-
"""Build the word rating table the golden traces need, from production.

The statistics pipeline reads ``GlobalDictionaryWord`` for every word in a log.
The golden test stubs that lookup out, so it needs a snapshot of E/D/lang for
exactly the words the fixture logs mention.

    python -m scripts.build_word_table --logs tests/fixtures/game_logs.jsonl \\
        --out tests/fixtures/word_ratings_prod.json

Read-only with respect to production.
"""

import argparse
import json
import logging
import os
import sys

logger = logging.getLogger(__name__)


def words_in_log(payload):
    """Every word a log refers to, in either format."""
    try:
        log = json.loads(payload)
    except ValueError:
        return []
    if log.get('version') == '2.0':
        return [event['word'] for event in log.get('attempts', [])
                if isinstance(event, dict) and 'word' in event]
    setup = log.get('setup') or {}
    return [entry['word'] for entry in setup.get('words', [])
            if isinstance(entry, dict) and 'word' in entry]


def _get_multi(ndb, model, ids, batch=500):
    out = []
    for start in range(0, len(ids), batch):
        chunk = ids[start:start + batch]
        out.extend(ndb.get_multi([ndb.Key(model, i) for i in chunk]))
    return out


def main():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--project", default="the-hat")
    args = parser.parse_args()

    os.environ["GOOGLE_CLOUD_PROJECT"] = args.project
    os.environ.pop("DATASTORE_EMULATOR_HOST", None)

    wanted = set()
    with open(args.logs, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                wanted.update(words_in_log(json.loads(line)["json"]))
    logger.info("%d distinct words referenced by the fixture logs", len(wanted))

    from google.cloud import ndb

    from app.models import GlobalDictionaryWord, WordLookup
    from scripts.gcloud_auth import ndb_client

    client = ndb_client(args.project)
    table = {}
    ordered = sorted(wanted)
    with client.context(cache_policy=lambda key: False):
        # Batched equivalent of GlobalDictionaryWord.get: direct hit first, then
        # the WordLookup alias table for whatever is left.
        direct = _get_multi(ndb, GlobalDictionaryWord, [w.lower() for w in ordered])
        missing = [w for w, found in zip(ordered, direct) if found is None]
        aliases = _get_multi(ndb, WordLookup, [w.lower() for w in missing])
        alias_targets = {w: a.proper_word for w, a in zip(missing, aliases) if a}
        resolved = _get_multi(ndb, GlobalDictionaryWord,
                              list(alias_targets.values()))
        by_alias = dict(zip(alias_targets, resolved))

        for word, entity in zip(ordered, direct):
            if entity is None:
                entity = by_alias.get(word)
            if entity is None:
                continue
            # Key by the word as the log spells it: the golden runner lowercases
            # before lookup, exactly like GlobalDictionaryWord.get.
            table[word] = {"E": entity.E, "D": entity.D,
                           "lang": entity.lang or "ru"}

    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(table, handle, ensure_ascii=False, indent=1, sort_keys=True)
    logger.info("%d of %d words are in the global dictionary -> %s",
                len(table), len(wanted), args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
