# -*- coding: utf-8 -*-
"""Recover the integer codes the legacy EnumProperty assigned to ignore reasons.

``GameLog.reason`` was an ``EnumProperty(IGNORE_REASON)``, which numbered the
reasons by iterating a dict -- so the numbering is whatever order CPython 2.7's
hash table happened to produce, and it is not recoverable by reading the source.

It is recoverable from the data: re-run the parser over every ignored GameLog in
production, see which ``BadGameError`` it raises, and correlate that with the
integer already stored on the entity.

    python -m scripts.recover_reason_enum --logs tests/fixtures/ignored_logs.jsonl

Read-only with respect to production.
"""

import argparse
import collections
import json
import logging
import sys

from app import stats

logger = logging.getLogger(__name__)


class Payload:
    def __init__(self, text):
        self.json = text


def classify(payload):
    """Return the reason ``add_game_to_statistic`` would record, or None."""
    try:
        (words_orig, seen_words_time, _outcome, _at_once, _pair,
         _players, _start, _finish) = stats.parse_log(Payload(payload))
    except stats.BadGameError as error:
        return error.reason
    except Exception as error:  # noqa: BLE001 - diagnostics only
        logger.debug("unparseable log: %s", error)
        return None

    if 2 * len(seen_words_time) < len(words_orig):
        return 'suspect_too_little_words'
    bad_words = sum(1 for value in seen_words_time.values() if value < 2)
    if 2 * bad_words > len(seen_words_time):
        return 'suspect_too_quick_explanation'
    return None


def main():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs", required=True,
                        help="JSONL from scripts/export_prod_logs.py --ignored")
    args = parser.parse_args()

    votes = collections.defaultdict(collections.Counter)
    total = 0
    unresolved = 0
    with open(args.logs, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if entry.get("reason") is None:
                continue
            total += 1
            reason = classify(entry["json"])
            if reason is None:
                unresolved += 1
                continue
            votes[entry["reason"]][reason] += 1

    logger.info("%d ignored logs, %d could not be re-classified", total, unresolved)
    mapping = {}
    for code in sorted(votes):
        counts = votes[code].most_common()
        winner, winner_count = counts[0]
        agreement = winner_count / float(sum(votes[code].values()))
        logger.info("code %s -> %s (%.0f%% of %d samples) %s",
                    code, winner, 100 * agreement, sum(votes[code].values()),
                    "" if agreement > 0.95 else "*** AMBIGUOUS ***")
        mapping[winner] = code

    print(json.dumps(mapping, indent=2, sort_keys=True))
    missing = set(stats_reason_names()) - set(mapping)
    if missing:
        logger.warning("no production sample for: %s", ", ".join(sorted(missing)))
    return 0


def stats_reason_names():
    from app.models import IGNORE_REASON

    return IGNORE_REASON.keys()


if __name__ == "__main__":
    sys.exit(main())
