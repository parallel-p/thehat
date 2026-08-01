# Migration notes — what the port actually did

Companion to `MIGRATION_PLAN.md`. The plan says what to build; this says what
was built, where reality differed from the plan, and which legacy bugs are
preserved on purpose.

## Deviations from the plan

### 1. `trueskill` could not simply be swapped for the PyPI package

The plan said "vendored `trueskill/` → PyPI `trueskill`". The vendored tree is
**not** stock trueskill 0.4.1: commit 07c69e8 (2014) added a `partial_update`
argument to `TrueSkill.rate`, and three of the four rating passes in the
statistics pipeline pass it. Stock trueskill would have raised `TypeError`, and
"fixing" that by dropping the argument would have silently changed every rating.

The patch is reapplied as a subclass in `app/trueskill_env.py` on top of PyPI
trueskill 0.4.5. Everything else in 0.4.5 is numerically identical to the
vendored 0.4.1 — verified by running both over 300 random rating groups (max
absolute difference 5.3e-13, pure floating-point noise from an algebraically
equivalent refactor of `LikelihoodFactor.calc_a`).

### 2. `GameLog.time` is not set at upload

Contract 1 in the plan says "`time=now`". The python27 code does not do that:
`time` is written later by the statistics task, from the log's own
`start_timestamp`. The code was followed, not the plan; `time` stays `None`
until the game is processed. This matters — `time` is what
`scripts/export_prod_logs.py --recent` orders by.

### 3. `UserDictionaryWord.added` is an `IntegerProperty`

The plan describes it as a `DateTimeProperty` whose `to_dict()` serialisation
needs care. It is an `IntegerProperty` in the python27 model, so `to_dict()`
produces a plain int and there is nothing to match.

### 4. `StringProperty(indexed=False)` had to become `TextProperty`

`google-cloud-ndb` refuses `StringProperty(indexed=False)`. In legacy ndb
`StringProperty` was literally `TextProperty` with `_indexed = True`, so
`TextProperty` is the wire-compatible spelling. Affects `GameLog.json`,
`GlobalDictionaryWord.tags` and `GlobalDictionaryWord.used_games`. Confirmed by
reading 3,700 real production entities through the new models.

### 5. The `reason` enum codes had to be recovered, not read

`GameLog.reason` was an `EnumProperty(IGNORE_REASON)` that numbered reasons by
iterating a dict — so the integers depend on CPython 2.7's hash ordering and are
not derivable from the source. They were recovered two independent ways, which
agree:

* running that iteration under python 2.7;
* re-classifying all 3,000 ignored `GameLog` entities in production with the
  ported parser and correlating with the stored integer
  (`scripts/recover_reason_enum.py`) — 100% agreement on codes 0 and 2.

Result (`app/models.py: REASON_CODES`): `suspect_too_little_words=0`,
`not_hat=1`, `suspect_too_quick_explanation=2`, `manual=3`, `old_version=4`,
`aborted=5`, `format-error=6`.

### 6. Cloud Tasks are pinned to the enqueueing version

Not in the plan, but necessary. During the WP8 split the python27 version still
serves most default traffic, so an unrouted task from the py3 version could be
delivered to the python27 handler, which cannot decode a py3 urlsafe key. Tasks
therefore set `app_engine_routing = {service, version: $GAE_VERSION}`.

## Python 2 → 3 traps that changed numbers

All three are in the rating pipeline and all three are covered by the golden
test; removing any of them makes it fail.

1. **`round()`**. Python 2 rounds halves away from zero, python 3 rounds halves
   to even. Explanation times are `round(milliseconds / 1000.0)`, which lands on
   exactly .5 whenever the millisecond value ends in 500 — common in real logs.
   `app/py2compat.py: py2_round`.
2. **Dict iteration order**. `seen_words_time` and `current_words_time` are keyed
   by small integer word indices. CPython 2.7 iterates such a dict in *slot*
   order, python 3 in insertion order. That order breaks ties when rating groups
   are sorted by explanation time, and a different tie order means different
   ranks and different ratings. `app/py2compat.py: Py2IntDict` emulates the 2.7
   hash table (`lookdict`/`insertdict`/`dictresize`/`PyDict_Clear`), and is
   checked against 268 operation sequences *measured* from real python 2.7
   (`tests/py2_reference/dump_dict_orders.py`), including sparse keys, deletions
   and `clear()`.
3. **Integer division**. `hour = game_time / 3600 % 168` and
   `failed_times / used_times` were floor division. Both use `//` now.

## Legacy bugs preserved deliberately

The python27 version keeps reading and writing the same entities during the
traffic split, so "fixing" these would make the two versions disagree.

* `GlobalDictionaryWord.danger` is `failed_times // used_times`, which is almost
  always 0. It is an indexed `ComputedProperty`, so changing it would rewrite an
  index the old version still queries.
* In `parse_log_v2`, `explained_at_once[n] = n not in seen_by_player.values()`
  compares an int against a collection of sets and is therefore always `True`.
* v1 logs whose `setup.type` is `freeplay` are rejected as `old_version`.

None of these should be changed before the python27 version is decommissioned
(WP9). After that they are fair game, but each one changes stored ratings.

## Dropped, as per plan §4

Pregame lobby, PIN numbers, settings sync, word streams/packages, complaints,
unknown-word admin, frequency dictionary, word-lookup admin, newsfeed (which had
a hardcoded password), Channel API notifications, matplotlib plots,
function-statistics (which `exec()`'d code stored in Datastore), link-device,
remove-duplicates, game results, save_game, web game creation, all admin pages,
appstats, remote_api, `/admin_panel`. All of them now 404 rather than 500 —
there is simply no route.

The three cron jobs are gone; `cron.yaml` deploys an empty list at cutover.
`/robots.txt` now disallows `/statistics/`, which was ~3.8k of the ~4k monthly
requests.

## Verification performed

| What | How |
|---|---|
| Rating pipeline | 700 real production logs + 90 synthetic; 7,764 `update_word` calls match the python27 code to <1e-9 |
| Dict-order emulation | 268 operation sequences measured from CPython 2.7 |
| trueskill replacement | 300 random rating groups vs the vendored 0.4.1, max diff 5.3e-13 |
| Dictionary blob format | byte-identical to the first 4,164 bytes of the blob production is serving |
| Enum codes | python 2.7 derivation + 3,000 production entities |
| Model compatibility | 3,700 production entities read through the new models |
| Contracts 1–8 | 100 pytest cases against the Datastore emulator |
