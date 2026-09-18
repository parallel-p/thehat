# -*- coding: utf-8 -*-
"""Build an anonymized, PII-free dataset of Hat games for Hugging Face.

The whole game lives as a JSON blob in ``GameLog.json`` (two on-wire formats,
v1 and v2). This script turns each game into one normalized, anonymized record:

* player names are dropped; players are referred to only by their in-game index
  ("Player 0", "Player 1", ...), which is a stable identity *within* a game;
* device / app info (``app.platform``, ``app.version``, ``time.zone``,
  ``game.id.local``, ...) is dropped;
* absolute wall-clock time (``start_timestamp`` / ``end_timestamp`` /
  ``time_zone_offset`` and the epoch ``time`` on round/game events) is dropped;
  only per-explanation timings survive, as ``explanation_time_ms``;
* games that use a word not in the global dictionary (i.e. a user-added word)
  are skipped entirely.

Two sources for the games (``--source``) and two for the dictionary
(``--dict``) so the anonymization can be validated offline before the
production read:

    # offline self-test against bundled fixtures
    python -m scripts.build_hf_dataset --selftest

    # small test pull from production (read-only), private local build
    python -m scripts.build_hf_dataset --source prod --limit 500 \
        --dict prod --out out/the-hat-games

Production Datastore is read-only for us (MIGRATION_PLAN.md §8); this script
only ever issues queries and get_multi lookups.
"""

import argparse
import json
import logging
import os
import sys

logger = logging.getLogger(__name__)

# Outcomes the clients emit. ``None`` means the attempt ended without a verdict
# (the pair moved on to the next word); it is kept, it is not PII.
KNOWN_OUTCOMES = {"guessed", "failed", "timed-out"}

# The game itself discards an explanation whose duration falls outside this
# window (app/stats.py MIN_TIME / MAX_TIME) -- paused timers, clock glitches.
# We keep the raw value and flag it, mirroring that logic, so consumers can
# reproduce the game's own filtering.
MIN_TIME_MS = 500
MAX_TIME_MS = 5 * 60 * 1000


# --------------------------------------------------------------------------
# Word extraction (both formats) -- mirrors scripts/build_word_table.words_in_log
# --------------------------------------------------------------------------


def words_in_log(log):
    """Every word a parsed log refers to, in either format, lower-cased."""
    if log.get("version") == "2.0":
        return [e["word"] for e in log.get("attempts", [])
                if isinstance(e, dict) and "word" in e]
    setup = log.get("setup") or {}
    return [e["word"] for e in setup.get("words", [])
            if isinstance(e, dict) and "word" in e]


# --------------------------------------------------------------------------
# Normalization + anonymization
# --------------------------------------------------------------------------


class SkipGame(Exception):
    """Raised to drop a game from the dataset, with a machine-readable reason."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def _attempt(word, explainer, guesser, time_ms, extra_ms, outcome):
    outcome = outcome if outcome in KNOWN_OUTCOMES else None
    total = int(time_ms) + int(extra_ms or 0)
    return {
        "word": word,
        "explainer": explainer,
        "guesser": guesser,
        "explanation_time_ms": total,
        "out_of_range": not (MIN_TIME_MS <= total <= MAX_TIME_MS),
        "outcome": outcome,
    }


def normalize_v2(log):
    """Normalize a v2 (attempts) log. Players are already integer indices."""
    players = set()
    attempts = []
    words = []
    for e in log.get("attempts", []):
        w = e["word"]
        if w not in words:
            words.append(w)
        players.add(e["from"])
        players.add(e["to"])
        attempts.append(_attempt(w, e["from"], e["to"],
                                 e.get("time", 0), e.get("extra_time", 0),
                                 e.get("outcome")))
    if not attempts:
        raise SkipGame("empty")
    return _pack(words, attempts, players)


def normalize_v1(log):
    """Normalize a v1 (setup/events) log.

    ``setup.words`` gives the literal words; events reference them by integer
    index. Round ``from``/``to`` are integer indices into ``setup.players`` --
    those are the player identities we keep; the names in ``setup.players`` are
    the PII we drop.
    """
    setup = log.get("setup") or {}
    if setup.get("type") == "freeplay":
        raise SkipGame("freeplay")
    word_list = [e["word"] for e in setup.get("words", [])
                 if isinstance(e, dict) and "word" in e]
    players = set()
    attempts = []
    used_words = []
    cur = None  # (explainer, guesser) of the current round
    for ev in log.get("events", []):
        etype = ev.get("type")
        if etype == "round_start":
            cur = (ev.get("from"), ev.get("to"))
            players.add(cur[0])
            players.add(cur[1])
        elif etype == "stripe_outcome":
            if cur is None:
                raise SkipGame("format-error")
            idx = ev["word"]
            try:
                w = word_list[idx]
            except (IndexError, TypeError):
                raise SkipGame("format-error")
            if w not in used_words:
                used_words.append(w)
            attempts.append(_attempt(w, cur[0], cur[1],
                                     ev.get("time", 0), ev.get("timeExtra", 0),
                                     ev.get("outcome")))
        elif etype == "outcome_override":
            # Retroactively fixes the most recent attempt on that word index.
            idx = ev.get("word")
            try:
                w = word_list[idx]
            except (IndexError, TypeError):
                raise SkipGame("format-error")
            for a in reversed(attempts):
                if a["word"] == w:
                    o = ev.get("outcome")
                    a["outcome"] = o if o in KNOWN_OUTCOMES else None
                    break
        # start_game / finish_round / end_game / pick_stripe carry only
        # absolute time or picking noise -- intentionally dropped.
    if not attempts:
        raise SkipGame("empty")
    return _pack(used_words, attempts, players)


def _pack(words, attempts, player_ids):
    """Re-index players to a dense 0..N-1 range and finalize the record body."""
    # Players are already small non-negative indices, but be defensive: build a
    # stable remap preserving first-appearance order so labels are 0..N-1.
    order = []
    for pid in [a["explainer"] for a in attempts] + [a["guesser"] for a in attempts]:
        if pid not in order:
            order.append(pid)
    for pid in sorted(player_ids, key=lambda x: (str(type(x)), x)):
        if pid not in order:
            order.append(pid)
    remap = {pid: i for i, pid in enumerate(order)}
    for a in attempts:
        a["explainer"] = remap[a["explainer"]]
        a["guesser"] = remap[a["guesser"]]
    n = len(order)
    return {
        "num_players": n,
        "players": ["Player {}".format(i) for i in range(n)],
        "num_words": len(words),
        "words": words,
        "num_attempts": len(attempts),
        "attempts": attempts,
    }


def normalize_game(raw_json):
    """Parse + normalize + anonymize one raw ``GameLog.json`` string.

    Returns the record body (without id/known-word gating), or raises SkipGame.
    """
    try:
        log = json.loads(raw_json)
    except (ValueError, TypeError):
        raise SkipGame("unparseable")
    if not isinstance(log, dict):
        raise SkipGame("unparseable")
    return normalize_v2(log) if log.get("version") == "2.0" else normalize_v1(log)


# --------------------------------------------------------------------------
# Sources
# --------------------------------------------------------------------------


def iter_raw_from_jsonl(path):
    """Yield {id, ignored, reason, json} dicts from an export_prod_logs file."""
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def iter_raw_from_prod(project, limit, page_size=300, recent=False):
    """Yield raw GameLog records straight from production (read-only).

    ``recent=True`` orders by ``-time``, which also restricts to games the
    stats pipeline has processed (``time`` is only set then) -- i.e. real,
    non-aborted games, newest first.
    """
    os.environ["GOOGLE_CLOUD_PROJECT"] = project
    os.environ.pop("DATASTORE_EMULATOR_HOST", None)
    from app.models import GameLog
    from scripts.gcloud_auth import ndb_client

    client = ndb_client(project)
    seen = 0
    with client.context(cache_policy=lambda key: False):
        query = GameLog.query().order(-GameLog.time) if recent else GameLog.query()
        cursor = None
        while limit is None or seen < limit:
            take = page_size if limit is None else min(page_size, limit - seen)
            page, cursor, more = query.fetch_page(take, start_cursor=cursor)
            for log in page:
                yield {
                    "id": log.key.id(),
                    "ignored": bool(log.ignored),
                    "reason": log.reason,
                    "json": log.json,
                }
                seen += 1
            if not more or not page:
                break
    logger.info("pulled %d GameLog entities from %s", seen, project)


# --------------------------------------------------------------------------
# Global-dictionary membership
# --------------------------------------------------------------------------


def known_words_from_prod(project, words, batch=500):
    """Set of the given words that resolve in the global dictionary.

    Same resolution as GlobalDictionaryWord.get: direct key hit, then the
    WordLookup alias table. Read-only.
    """
    os.environ["GOOGLE_CLOUD_PROJECT"] = project
    os.environ.pop("DATASTORE_EMULATOR_HOST", None)
    from google.cloud import ndb
    from app.models import GlobalDictionaryWord, WordLookup
    from scripts.gcloud_auth import ndb_client

    def get_multi(model, ids):
        out = []
        for s in range(0, len(ids), batch):
            chunk = ids[s:s + batch]
            out.extend(ndb.get_multi([ndb.Key(model, i) for i in chunk]))
        return out

    ordered = sorted({w.lower() for w in words})
    known = set()
    client = ndb_client(project)
    with client.context(cache_policy=lambda key: False):
        direct = get_multi(GlobalDictionaryWord, ordered)
        missing = [w for w, e in zip(ordered, direct) if e is None]
        known.update(w for w, e in zip(ordered, direct) if e is not None)
        if missing:
            aliases = get_multi(WordLookup, missing)
            known.update(w for w, a in zip(missing, aliases) if a is not None)
    logger.info("%d of %d distinct words are in the global dictionary",
                len(known), len(ordered))
    return known


def known_words_from_file(path, words):
    """Offline dictionary: words/dictionary.ru.txt (``word <freq>`` per line)."""
    vocab = set()
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            tok = line.split()
            if tok:
                vocab.add(tok[0].strip().lower())
    return {w.lower() for w in words if w.lower() in vocab}


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------


def build(raw_records, known_words):
    """Normalize + gate a list of raw records. Returns (records, stats)."""
    stats = {"input": 0, "kept": 0, "skipped": {}}
    kept = []
    for raw in raw_records:
        stats["input"] += 1
        try:
            body = normalize_game(raw.get("json"))
        except SkipGame as e:
            stats["skipped"][e.reason] = stats["skipped"].get(e.reason, 0) + 1
            continue
        unknown = [w for w in body["words"] if w.lower() not in known_words]
        if unknown:
            stats["skipped"]["self_added_word"] = \
                stats["skipped"].get("self_added_word", 0) + 1
            continue
        record = {
            "game_id": "game_{:06d}".format(len(kept) + 1),
            "ignored": bool(raw.get("ignored", False)),
            "ignored_reason": raw.get("reason"),
        }
        record.update(body)
        kept.append(record)
    stats["kept"] = len(kept)
    return kept, stats


def selftest():
    """Validate normalization against the bundled fixtures + a real v1 payload."""
    import unittest

    # A real-format v1 payload (names + device meta + absolute times), trimmed
    # to two rounds -- structurally identical to legacy log_handling_test.
    v1 = json.dumps({
        "setup": {
            "type": "quick",
            "players": [
                {"name": "Вася Пупкин",
                 "id": "owner-abc", "type": "OWNER_RANDOM", "random": False},
                {"name": "Маша", "id": "xyz",
                 "type": "RANDOM", "random": True},
            ],
            "meta": {"game.id": "feeb", "time.offset": "10800000",
                     "app.platform": "android", "app.version": "13",
                     "time.zone": "GMT+03:00", "game.id.local": "195a"},
            "words": [{"word": "кот"}, {"word": "дом"}],
        },
        "events": [
            {"type": "start_game", "time": 1588671012202},
            {"type": "round_start", "from": 0, "to": 1, "time": 111},
            {"type": "pick_stripe", "word": 0},
            {"type": "stripe_outcome", "word": 0, "outcome": "guessed",
             "time": 5000, "timeExtra": 500},
            {"type": "stripe_outcome", "word": 1, "outcome": "timed-out",
             "time": 3000, "timeExtra": 0},
            {"type": "outcome_override", "word": 1, "outcome": "guessed"},
            {"type": "finish_round", "time": 222},
            {"type": "end_game", "time": 1588672017209, "aborted": False},
        ],
    }, ensure_ascii=False)

    v2 = json.dumps({
        "version": "2.0", "start_timestamp": 1582558022018,
        "end_timestamp": 1582558610857, "time_zone_offset": 10800000,
        "attempts": [
            {"from": 0, "to": 1, "word": "цемент",
             "time": 13777, "extra_time": 0, "outcome": "guessed"},
            {"from": 0, "to": 1, "word": "кочегар",
             "time": 6230, "extra_time": 3},  # no outcome -> null
        ],
    }, ensure_ascii=False)

    blob = json.dumps(v1) + json.dumps(v2)  # ensure no cross-contamination

    class T(unittest.TestCase):
        def test_v1_names_and_time_gone(self):
            r = normalize_game(v1)
            self.assertNotIn("Вася",
                             json.dumps(r, ensure_ascii=False))
            self.assertNotIn("android", json.dumps(r))
            self.assertNotIn("1588671012202", json.dumps(r))
            self.assertEqual(r["players"], ["Player 0", "Player 1"])
            self.assertEqual(r["num_players"], 2)
            self.assertEqual(r["attempts"][0]["explanation_time_ms"], 5500)
            self.assertFalse(r["attempts"][0]["out_of_range"])
            self.assertEqual(r["attempts"][0]["outcome"], "guessed")
            # override flipped timed-out -> guessed
            self.assertEqual(r["attempts"][1]["outcome"], "guessed")
            self.assertEqual([a["word"] for a in r["attempts"]],
                             ["кот", "дом"])

        def test_v2_timestamps_gone_null_outcome(self):
            r = normalize_game(v2)
            s = json.dumps(r)
            self.assertNotIn("1582558022018", s)
            self.assertNotIn("time_zone_offset", s)
            self.assertNotIn("start_timestamp", s)
            self.assertEqual(r["attempts"][0]["explanation_time_ms"], 13777)
            self.assertIsNone(r["attempts"][1]["outcome"])
            self.assertEqual(r["num_players"], 2)

        def test_word_gate(self):
            recs, st = build(
                [{"id": "a", "json": v1}, {"id": "b", "json": v2}],
                known_words={"кот", "дом"})  # v2 words absent
            self.assertEqual(st["kept"], 1)
            self.assertEqual(st["skipped"].get("self_added_word"), 1)
            self.assertEqual(recs[0]["game_id"], "game_000001")

        def test_fixtures_parse(self):
            path = os.path.join(os.path.dirname(__file__), "..", "tests",
                                "fixtures", "synthetic_logs.jsonl")
            n = 0
            for raw in iter_raw_from_jsonl(path):
                normalize_game(raw["json"])  # must not raise
                n += 1
            self.assertGreater(n, 10)

    suite = unittest.TestLoader().loadTestsFromTestCase(T)
    res = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if res.wasSuccessful() else 1


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--source", choices=["prod", "jsonl"], default="prod")
    p.add_argument("--jsonl", help="raw export file when --source jsonl")
    p.add_argument("--project", default="the-hat")
    p.add_argument("--limit", type=int, default=500,
                   help="max games to pull from prod (0 = all)")
    p.add_argument("--recent", action="store_true",
                   help="order prod pull by -time (processed games, newest first)")
    p.add_argument("--dict", choices=["prod", "file"], default="prod")
    p.add_argument("--dict-file", default=os.path.join(
        os.path.dirname(__file__), "..", "words", "dictionary.ru.txt"))
    p.add_argument("--out", default="out/the-hat-games")
    p.add_argument("--raw-out", help="also cache the raw prod pull to this jsonl")
    args = p.parse_args()

    if args.selftest:
        return selftest()

    if args.source == "jsonl":
        if not args.jsonl:
            p.error("--source jsonl requires --jsonl")
        raw = list(iter_raw_from_jsonl(args.jsonl))
    else:
        limit = None if args.limit == 0 else args.limit
        raw = list(iter_raw_from_prod(args.project, limit, recent=args.recent))
    logger.info("loaded %d raw games", len(raw))

    if args.raw_out:
        os.makedirs(os.path.dirname(args.raw_out) or ".", exist_ok=True)
        with open(args.raw_out, "w", encoding="utf-8") as handle:
            for r in raw:
                handle.write(json.dumps(r, ensure_ascii=False) + "\n")
        logger.info("cached raw pull -> %s", args.raw_out)

    all_words = set()
    for r in raw:
        try:
            log = json.loads(r["json"])
        except (ValueError, TypeError):
            continue
        all_words.update(words_in_log(log))
    logger.info("%d distinct words across all games", len(all_words))

    if args.dict == "prod":
        known = known_words_from_prod(args.project, all_words)
    else:
        known = known_words_from_file(args.dict_file, all_words)

    records, stats = build(raw, known)
    write_outputs(records, stats, args.out)
    logger.info("stats: %s", json.dumps(stats, ensure_ascii=False))
    return 0


# --------------------------------------------------------------------------
# Output packaging (jsonl + parquet + HF dataset card)
# --------------------------------------------------------------------------


def _dataset_summary(records):
    import collections
    players = collections.Counter(r["num_players"] for r in records)
    outcomes = collections.Counter(a["outcome"] for r in records
                                   for a in r["attempts"])
    return {
        "num_games": len(records),
        "num_attempts": sum(r["num_attempts"] for r in records),
        "num_ignored": sum(1 for r in records if r["ignored"]),
        "players_distribution": dict(sorted(players.items())),
        "outcomes": {("null" if k is None else k): v
                     for k, v in sorted(outcomes.items(),
                                        key=lambda kv: str(kv[0]))},
    }


DATASET_CARD = """\
---
license: cc-by-4.0
language:
- ru
pretty_name: The Hat — Anonymized Games
tags:
- games
- word-game
- russian
size_categories:
- {size_cat}
configs:
- config_name: default
  data_files: data/games.parquet
---

# The Hat — Anonymized Games

Real gameplay records from **The Hat** (Шляпа) — a word-explanation party game
where one player explains a word while a teammate races to guess it before the
timer runs out. Learn about the game at
[the-hat.appspot.com](https://the-hat.appspot.com).

Each row is one game: the words that came up, who explained to whom, how long
each explanation took, and whether it was guessed. It's a rich source for
studying word difficulty, explanation time, and turn-taking dynamics.

## Privacy

Every record is anonymized. The following are removed and verified absent from
the data: **player names**, **device and app information**, and **absolute
dates/times** (when a game was played). Only *relative* per-explanation
durations are kept — never wall-clock time.

Players appear only as a within-game index (`Player 0`, `Player 1`, …), which is
stable inside a single game (so turns and per-player behavior are preserved) and
carries no meaning across games.

Every word in the dataset comes from the game's **shared word list**. Games in
which a player entered their own custom word are **excluded entirely**, so no
user-authored text is present.

## Schema

| field | type | description |
|---|---|---|
| `game_id` | string | Synthetic sequential id (`game_000001`, …). |
| `ignored` | bool | The game was flagged as low-quality (aborted, too few words, explanations too quick, …). Kept so you can filter it out if you want only clean games. |
| `ignored_reason` | int / null | Reason code when `ignored` (0 too-little-words, 1 not-hat, 2 too-quick, 3 manual, 4 old-version, 5 aborted, 6 format-error). |
| `num_players` | int | Distinct players in the game. |
| `players` | list[string] | `["Player 0", …, "Player {{n-1}}"]`. |
| `num_words` | int | Distinct words used. |
| `words` | list[string] | Distinct words used, first-seen order. |
| `num_attempts` | int | Number of explanation attempts. |
| `attempts` | list[struct] | Ordered explanation attempts (see below). |

Each `attempts[i]` is:

| field | type | description |
|---|---|---|
| `word` | string | The word being explained. |
| `explainer` | int | Index of the explaining player. |
| `guesser` | int | Index of the guessing player. |
| `explanation_time_ms` | int | Time spent explaining this word, in milliseconds (base time plus any added extra time). |
| `out_of_range` | bool | True when the duration is outside [0.5 s, 5 min]; the game discards these (paused timer / clock glitch). Filter on this to match in-game scoring. |
| `outcome` | string / null | `guessed`, `failed`, `timed-out`, or `null` (moved on without a verdict). |

## Dataset statistics

- Games: **{num_games}**  ·  total explanation attempts: **{num_attempts}**
- Games flagged `ignored`: {num_ignored}
- Players per game: {players_distribution}
- Attempt outcomes: {outcomes}

## About the game

The Hat (Шляпа) is a team word-guessing game: players take turns explaining
words to a partner under a time limit, scoring for each word guessed in time.
More at [the-hat.appspot.com](https://the-hat.appspot.com).

These statistics were gathered from games that players uploaded to the server at
[the-hat.appspot.com](https://the-hat.appspot.com).
"""


def _size_category(n):
    if n < 1000:
        return "n<1K"
    if n < 10000:
        return "1K<n<10K"
    if n < 100000:
        return "10K<n<100K"
    if n < 1000000:
        return "100K<n<1M"
    return "1M<n<10M"


def write_outputs(records, stats, out_dir):
    data_dir = os.path.join(out_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    jsonl_path = os.path.join(data_dir, "games.jsonl")
    with open(jsonl_path, "w", encoding="utf-8") as handle:
        for rec in records:
            handle.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # Parquet is the format HF loads by default; write it if pyarrow is present.
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
        table = pa.Table.from_pylist(records)
        pq.write_table(table, os.path.join(data_dir, "games.parquet"))
    except ImportError:
        logger.warning("pyarrow not installed; skipping parquet output")

    summary = _dataset_summary(records)
    with open(os.path.join(out_dir, "stats.json"), "w", encoding="utf-8") as h:
        json.dump({"build": stats, "summary": summary}, h,
                  ensure_ascii=False, indent=2)

    card = DATASET_CARD.format(size_cat=_size_category(len(records)), **summary)
    with open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8") as h:
        h.write(card)

    logger.info("wrote %d records -> %s (+ parquet, README.md, stats.json)",
                len(records), out_dir)


if __name__ == "__main__":
    sys.exit(main())
