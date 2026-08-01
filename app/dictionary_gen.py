# -*- coding: utf-8 -*-
"""Dictionary generation -- the port of ``GenerateDictionary`` (WP6).

Run as a one-off job:

    GOOGLE_CLOUD_PROJECT=the-hat-staging python -m app.dictionary_gen

It is deliberately not exposed as an HTTP endpoint: there is no admin UI in the
py3 app, and this is the only write-heavy operation left.

Output format is byte-compatible with the blob the python27 job produced. Two
details make that true and are easy to break:

* ``json.dump`` on python2 emitted ASCII escapes (``ensure_ascii=True``, still
  the default in python3) and ``', '`` / ``': '`` separators.
* the per-word dict was built as ``{"word", "diff", "used", "tags"}`` but python2
  serialised it in hash order, which for these four keys is
  ``diff, used, word, tags``. Python3 preserves insertion order, so the keys are
  inserted in that order here.
"""

import argparse
import json
import logging
import time

from app import storage
from app.models import Dictionary, GlobalDictionaryWord
from app.ndb_ctx import with_context

logger = logging.getLogger(__name__)


def build_payload(words):
    """Serialise ``words`` exactly the way the python27 job did."""
    chunk_size = len(words) // 100
    data_object = []
    for i, word in enumerate(words):
        data_object.append({
            "diff": i // chunk_size,
            "used": word.used_times,
            "word": word.word,
            "tags": word.tags,
        })
    return json.dumps(data_object).encode("utf-8")


def generate_one(dictionary, dry_run=False):
    lang = dictionary.key.id()
    words = GlobalDictionaryWord.query(
        GlobalDictionaryWord.deleted == False,  # noqa: E712 -- ndb needs ==
        GlobalDictionaryWord.lang == lang,
    ).order(GlobalDictionaryWord.E).fetch()
    if not words:
        logger.warning("no words for lang %s, skipping", lang)
        return None

    payload = build_payload(words)
    key = str(int(time.time()))
    logger.info("lang=%s words=%d new_key=%s bytes=%d",
                lang, len(words), key, len(payload))
    if dry_run:
        return payload

    storage.write_dictionary_blob(key, payload)
    old_key = dictionary.gcs_key
    dictionary.gcs_key = key
    dictionary.put()
    if old_key and old_key != key:
        storage.delete_dictionary_blob(old_key)
    return payload


@with_context
def generate(dry_run=False):
    results = {}
    for dictionary in Dictionary.query():
        results[dictionary.key.id()] = generate_one(dictionary, dry_run=dry_run)
    return results


def main():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="build the payload but do not write anything")
    parser.add_argument("--out", help="write the generated payload to this file")
    args = parser.parse_args()

    results = generate(dry_run=args.dry_run)
    if args.out:
        for lang, payload in results.items():
            if payload is None:
                continue
            path = args.out if len(results) == 1 else "{}.{}".format(args.out, lang)
            with open(path, "wb") as handle:
                handle.write(payload)
            logger.info("wrote %s", path)


if __name__ == "__main__":
    main()
