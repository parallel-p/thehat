# Шляпа as a PWA — plan

Replacing [beret](https://github.com/nzinov/beret) — the Flutter app currently
advertised at `/android/new/beta` — with an offline-capable web app served from
this repo, installable on both Android and iOS.

Branch: `pwa/plan`, cut from `migration/py3`.

## Status

**Built and deployed to staging.** WP1–WP7 and WP9–WP10 are done and live at
`/play`; the plan below is kept as the record of why it is shaped this way,
with the three findings from building it in §11.

Not done: WP8 was folded into the build (the app takes `assets/hat.css` whole
rather than being restyled afterwards), and nothing has been verified on real
iPhone or Android hardware — only in Chrome at phone widths, including a
genuine offline start with the server killed.

## 0. Decisions

Settled, so the rest of this document assumes them:

1. **Written by hand**, not `flutter build web`. Plain ES modules, no framework,
   no bundler, the site's own CSS. Rationale in §3.
2. **First release is both game modes and nothing else** — быстрая игра and
   режим для двоих, offline, log upload, install. No game history, no rules
   screen, no authors page, no word complaints.
3. **The PWA replaces the Android app.** The landing page and the two
   `/android/*` pages stop offering the APK and point at `/play`.
4. **Server work: game-id de-duplication and `Cache-Control` on the
   dictionary.** Complaints are not restored.

### 0.1 What decisions 2 and 3 cost, taken together

Retiring the app while shipping less than parity means these go away and do not
come back:

- **Game history.** Beret keeps `gameHistory.json` locally and shows past
  scoreboards. Nothing migrates: an existing player's history dies with the
  APK, and the PWA does not start keeping one. It is a day of work to add later
  (the data is already in the log the app builds) but it is not in v1.
  *Since added* — `/play` keeps its own, in a `history` store, capped at fifty
  games. An existing player's beret history still does not migrate.
- **Word complaints.** The only channel for a player to flag an offensive or
  broken word disappears from the client. It has in fact been broken since the
  migration removed the endpoint, so nothing is *lost* today — but the decision
  not to restore it means the dictionary keeps no player-facing vetting path.
  Worth revisiting once §8.1 is in.
- **The rules screen.** Acceptable: the rules already live on the site at
  `thehat.ru/rules/`, and `/play` can link to them. *Since added* — the text
  is carried in the shell instead, copied from `beret/lib/rules.dart`, because
  a link is no use at a table with no signal.

Of what beret had, that leaves the authors/credits page and word complaints
outside `/play` by choice; complaints would need the server endpoint back
(§8.1) before the client could mean anything by them.

None of this blocks the plan. It is written down so that retiring the APK is a
choice made with the bill visible.

### 0.2 Legacy installs keep double-posting

Decision 3 retires the app from the *site*, but installed copies keep running.
Per §1.6 each of them stores every game twice, and the game-id de-duplication
in §8.1 cannot help them — old clients send no id. Expect the duplicate rate to
decay as installs go stale rather than stop on cutover day. If that matters,
the cheap fix is a server-side heuristic (§8.1).

---

## 1. What beret actually does

Read from the source at `nzinov/beret@6c67a65` (Dart, ~4.5k lines in `lib/`).
This is the inventory the PWA has to match; nothing below is guesswork.

### 1.1 Home (`main.dart`)

Four tiles: **Быстрая игра**, **Режим для двоих**, **Правила**, **История игр**,
plus авторы/настройки. On first run it loads the dictionary and generates a
`deviceId` (UUID v4) kept in preferences.

### 1.2 Быстрая игра — the party game (`match.dart`, `game_state.dart`, `turn.dart`)

- **Lobby**: a list of players (default two, «Игрок N»), add/remove/rename,
  validated to be non-empty and unique. Per-match settings: words per player
  (default 10), round length (`mainStateLength`, default 20 s), extra time
  (`lastStateLength`, default 3 s), difficulty (`matchDifficulty`, default 30),
  dispersion (`difficultyDispersion`, default 15), fixed teams on/off.
- **Pairing**: with `fixTeams` off, the explainer is `turn % n` and the guesser
  rotates so everyone eventually explains to everyone. With `fixTeams` on,
  players are paired `2k`/`2k+1` and the direction flips halfway. Both formulas
  are in `getPlayerOneId`/`getPlayerTwoId` and must be ported verbatim — they
  are the difference between "личная игра" and "парная игра" in the rules.
- **Hat**: `wordsPerPlayer × players` words drawn once at match start
  (`createHat`), then sampled without replacement; unguessed words go back.
- **Turn**: 3-2-1 countdown → `main` state for `mainStateLength` seconds →
  `last` state for `lastStateLength` seconds (the guesser's last chance at one
  word) → `verdict`. Buttons: **Угадано**, **Ошибка**, **Сдаться**.
- **Verdict / round editing** (`RoundEditing`): every word of the round is
  listed and its outcome can still be changed (guessed ↔ failed), the word can
  be revealed, or complained about. Then «дальше» or «закончить игру».
- **Scoreboard**: per player explained/guessed counts, per team when teams are
  fixed. Written to game history at the end.
- **Sounds**: tick, round start, round timeout, word ok/fail/timeout.

### 1.3 Режим для двоих — deathmatch (`deathmatch_state.dart`, `deathmatch.dart`)

Single-pair endurance mode. 60 s main clock plus a per-word bonus clock
(`additionalTime`, starts at 10 s). Every guessed word adds one to the score,
resets the bonus and draws a new word. **Every 5 points the game gets harder**:
either difficulty `+5` (capped at 100) or bonus time `−1` (floored at 0), chosen
at random, and the changed number blinks. Ends when the main clock runs out or
the player concedes.

### 1.4 Dictionary and word selection (`dictionary.dart`)

- Downloads `GET /api/v2/dictionary/ru` and caches it (`flutter_cache_manager`).
- Buckets words into 101 lists by their `diff` field (0…100), drops
  `tags == '-deleted'`, shuffles each bucket.
- **Sampling**: a bucket index is drawn from `Normal(difficulty,
  dispersion² / 9)`, resampled while outside 0…100; the word is taken from that
  bucket's shuffle order.
  **Verify before porting:** if `normal`'s second argument is the variance then
  σ = dispersion / 3, i.e. 5 at the default dispersion of 15, which is the
  reading that makes the setting sensible; if it is the standard deviation,
  σ = 75 and the setting does nothing. Read the package, then match the
  *observed* histogram (WP2), not the formula.
- **Repeat avoidance**: a 1000-slot ring buffer of recently used words
  (`used_words.json` + `usedWordsIter`), consulted on every draw.

### 1.5 Server sync (`app_state.dart`, `turn.dart`)

- `POST /api/v2/game/log` with the v2 log; on failure the log is appended to
  `gameLogs.json` and retried every 5 minutes.
- `POST /{deviceId}/complain` for word complaints, queued the same way.
- Everything else is local.

### 1.6 Two bugs worth not reproducing

- `sendSingleGameLog` treats anything other than **201** as failure, but
  `/api/v2/game/log` answers **202** (`app/api_v2.py`). Every log is therefore
  queued as "failed" and sent a second time by the periodic sync. The server
  stores logs verbatim and enqueues a stats task per log, so **each game is
  currently counted roughly twice**. The PWA must accept 2xx.
- The complaint endpoint no longer exists: complaints were dropped in the
  python3 migration (`app/main.py` header), so every complaint the app has
  taken since then went nowhere. The PWA drops the feature (§0.1).

---

## 2. Server contracts the PWA depends on

| Endpoint | Used for | Status |
|---|---|---|
| `GET /api/v2/dictionary/ru` | word list | exists, ETag-cached (`app/api_v2.py`); gains `Cache-Control` (§8.2) |
| `POST /api/v2/game/log` | game upload → 202 | exists; gains `game_id` (§8.1) |
| `GET /api/v2/dictionaries` | language list | exists, unused in v1 (`ru` only) |
| `POST /{deviceId}/complain` | word complaints | gone, and staying gone (§0.1) |

Production `ru` dictionary today: **13 799 words, 1.29 MB raw, 138 KB gzipped**,
101 difficulty buckets of 99–137 words each. That is small enough to hold
offline in full, which is what makes this feasible.

### 2.1 The log format is a hard contract

`stats.parse_log_v2` is what turns a log into word ratings. The PWA must emit
exactly:

```json
{ "version": "2.0",
  "start_timestamp": 1700000000000,     // ms since epoch, game start
  "end_timestamp":   1700001800000,
  "time_zone_offset": 10800000,          // ms; added server-side before bucketing
  "attempts": [
    {"word": "ковчег", "from": 0, "to": 1,
     "time": 8000, "extra_time": 0, "outcome": "guessed"}
  ] }
```

Rules the parser imposes, all of which the PWA must respect:

- `outcome` is `"guessed"`, `"failed"`, or **absent** (word returned to the hat).
  Absent is not the same as failed — it means "ran out of time".
- `time + extra_time` outside **500 ms … 5 min** marks the word `removed` and it
  is dropped from rating.
- A game is rejected wholesale (`suspect_too_little_words`) if fewer than half
  the words in the hat were attempted, and (`suspect_too_quick_explanation`) if
  more than half the attempts took under 2 s.
- `from`/`to` are player indices; the count of distinct indices becomes the
  reported player count.
- **`time_zone_offset` matters**: the server adds it to `start_timestamp` before
  bucketing the hour, so the statistics pages show each player's own evening.
  See the comment in `app/web.py:total_statistics`.

A round-trip test against `parse_log_v2` is the single most important test in
this project (§7, WP6).

---

## 3. Why by hand

`flutter build web` was the alternative and beret already has a `web/` target,
so it was the fast path. Rejected because the CanvasKit bundle is ~2 MB before
the app's own code, it paints text to a canvas (no selection, no real
accessibility), it looks nothing like the rest of the site, and it drags a
Flutter SDK into a repo whose discipline is *no CDN, no third-party request, no
build step*. None of that buys anything on the parts that are actually hard —
offline storage, the log contract, and what iOS does to timers, audio and
stored data are identical either way, and a framework that hides the platform
makes them worse.

So: ~1 500–2 000 lines of plain ES modules, the site's CSS tokens, first load
well under 100 KB plus the dictionary.

One consequence to state plainly: **this introduces JavaScript to a codebase
that currently has none**, and DESIGN.md says so as a rule. That rule is about
the marketing and statistics pages, which must render as documents. An app that
runs a stopwatch is a different thing, and the rule gets amended rather than
quietly broken — the pages stay no-JS, `/play` is allowed script.

---

## 4. Where it lives

```
static/play/               # served as static files, no template rendering
  index.html               # app shell (one document, screens are sections)
  app.css                  # imports the site's tokens from /assets/hat.css
  sw.js                    # service worker, served from /play/ scope
  manifest.webmanifest
  js/
    state.js               # the store: game + deathmatch state machines
    dictionary.js          # fetch, bucket, sample, used-word ring
    log.js                 # v2 log assembly + outbox
    db.js                  # IndexedDB wrapper
    audio.js  timer.js  ui.js
  icons/                   # 192/512 png + maskable + apple-touch-icon
  sounds/                  # the six wavs from beret/assets, re-encoded
```

`app.yaml` gains, **above** the catch-all:

```yaml
- url: /play
  static_files: static/play/index.html
  upload: static/play/index\.html
  mime_type: text/html
- url: /play/sw\.js
  static_files: static/play/sw.js
  upload: static/play/sw\.js
  mime_type: application/javascript
  http_headers:
    Service-Worker-Allowed: /play/
- url: /play/(.*)
  static_files: static/play/\1
  upload: static/play/.*
```

### 4.1 Origin

Checked rather than assumed: `thehat.ru` is a separate nginx host (404 at the
root today; it serves `/rules/`), and `gcloud app domain-mappings list` returns
nothing, so this App Engine app answers on `the-hat.appspot.com` and nothing
else. Serving `/play` from here is therefore same-origin with `/api/v2/*` for
free — no CORS, and the service worker can cache API responses.

If a custom domain is mapped later, the manifest `start_url`/`scope` and the
service worker scope are the only things that need to follow.

### 4.2 Cutover (decision 3)

- Landing page: «Скачать приложение» → «Играть», linking `/play`. The «Новое
  приложение»/«Старое приложение» pair in the last section collapses to one
  link.
- `/android/new/beta` (currently the APK from `github.com/nzinov/beret/releases`)
  and `/android/beta` (the 2014 Play Store build) both become short pages that
  point at `/play` and keep the APK link only as a footnote for people who
  already have it. Killing the URLs outright would break inbound links from
  F-Droid and VK.
- Nav «Скачать» → «Играть».

---

## 5. Offline architecture

### 5.1 Three storage tiers

| What | Where | Why |
|---|---|---|
| shell (html/css/js/icons/sounds) | Cache Storage, precached by `sw.js` | must survive a cold offline start |
| dictionary (13.8k words) | IndexedDB, one record per difficulty bucket | needs random access by bucket; too big to re-parse per draw |
| used-word ring, settings, history, log outbox | IndexedDB | mutable, must survive reloads |

Settings stay in IndexedDB too rather than `localStorage`, so there is exactly
one storage API to reason about when Safari evicts.

### 5.2 Service worker strategy

- **Install**: precache the shell under a version-stamped cache name.
- **Activate**: delete old caches, `clients.claim()`.
- **Fetch**: cache-first for shell assets; network-only for `/api/v2/game/log`
  (the outbox handles failure, the SW must never queue a POST silently);
  stale-while-revalidate for the dictionary URL.
- The shell is a single HTML document, so navigation requests fall back to the
  cached `/play` on failure — no per-route offline gaps.

### 5.3 Dictionary lifecycle

1. First run: fetch, bucket, write 101 records + the ETag, in one transaction.
2. Later runs: read from IndexedDB immediately, **then** revalidate in the
   background with `If-None-Match`. A 304 costs nothing; a 200 rebuilds the
   buckets and takes effect next game, never mid-game.
3. No network ever: run from the stored copy. The app is fully playable.
4. Never fetched at all (installed offline): show a clear "нужно один раз
   выйти в сеть" state rather than an empty hat.

### 5.4 Outbox

Finished logs go to an `outbox` store, then:

- flush immediately if online;
- on `online` events and on app start;
- via **Background Sync** where available (Chromium/Android);
- on iOS, where Background Sync does not exist, on next open. Logs are small;
  a week of games is a few KB.

Flush deletes a log only on a **2xx** response (see §1.6). Each log carries a
client-side UUID so a re-send after an ambiguous failure can be de-duplicated —
which needs a server-side change to be useful (§8).

---

## 6. The platform problems, and what each costs

These are the reasons this is not "just write a web page", listed with the
mitigation each needs.

**Timers must not count ticks.** `setInterval` is throttled in background tabs
and stops when an iOS screen locks. Every clock derives from
`performance.now()` deltas against a start timestamp; the interval only
repaints. Verify by locking the phone mid-round.

**Screen wake lock.** `navigator.wakeLock` — Chrome Android yes, iOS Safari
16.4+ yes. Request on round start, release on verdict, re-request on
`visibilitychange` (the lock is dropped when the tab hides). Below 16.4 there is
no fallback worth the hack; the round is 20 s and the display timeout is
usually longer.

**Audio needs a gesture.** iOS will not play until an `AudioContext` is resumed
inside a user gesture. Unlock on the first tap anywhere and keep one context for
the session; decode the six sounds once into buffers. Also honour the iOS
silent switch by not depending on sound alone — every sound has a visual
counterpart.

**iOS storage eviction.** Safari's ITP clears site data after ~7 days without
interaction, which would silently delete a 13k-word dictionary and any queued
logs. Call `navigator.storage.persist()` on first launch (granted for installed
PWAs); detect eviction on start (dictionary missing but settings present) and
re-fetch. This is the single most likely field failure and needs an explicit
test: install, don't open for a week, open offline.

**Install prompt.** Android gets `beforeinstallprompt` and a real button. iOS
has none — it needs `apple-mobile-web-app-capable`, an `apple-touch-icon`, and
an in-page instruction shown only to iOS Safari visitors who are not already
standalone. Say "Поделиться → На экран «Домой»" and show it once.

**Viewport.** `viewport-fit=cover`, `env(safe-area-inset-*)` padding, and
`100dvh` rather than `100vh` — the round screen is full-bleed and iOS toolbars
will otherwise cover the buttons.

**No wake from sleep, no notifications.** Beret has none either. Not in scope.

---

## 7. Work packages

Each ends in something checkable. WP1–WP6 are the app; WP7–WP9 make it good.

**WP1 — Skeleton and routing.** `static/play/` shell, `app.yaml` handlers, the
site's CSS tokens, a home screen with four tiles, `/play` reachable on staging.
*Done when:* `/play` renders on staging and Lighthouse's PWA audit passes
except for offline.

**WP2 — Dictionary offline.** `db.js`, fetch + bucket + store, ETag
revalidation, the sampler (normal draw, resample, ring buffer) ported from
`dictionary.dart`.
*Done when:* a unit test draws 10 000 words at difficulty 30 / dispersion 15 and
the histogram matches σ = 5 within tolerance, no word repeats inside 1000 draws,
and the app draws words with the network disabled.

**WP3 — Service worker.** Precache, activate, fetch strategies, update flow
(new version banner, `skipWaiting` on user consent).
*Done when:* airplane mode, cold start, full game playable.

**WP4 — Быстрая игра.** Lobby, pairing formulas, turn state machine, timers,
verdict, round editing, end-of-game scoreboard. No persisted history (§0.1) —
the scoreboard is shown and then dropped.
*Done when:* a 6-player game plays start to finish and the scoreboard matches
hand-counted outcomes.

**WP5 — Режим для двоих.** Deathmatch state machine including the every-5-points
escalation and the blink.
*Done when:* difficulty/bonus escalate as in `deathmatch_state.dart`.

**WP6 — Logs.** v2 assembly, outbox, flush, background sync. **The test that
matters:** a golden log produced by the PWA is fed to `stats.parse_log_v2` in
this repo's test suite and must yield the expected words, outcomes, times and
player count — the same way `tests/test_stats_datastore.py` already exercises
the pipeline.
*Done when:* a game played on staging appears in `/statistics/word_statistics`
with the right words moved.

**WP7 — Install and iOS polish.** Manifest, icons, `beforeinstallprompt`, iOS
instructions, safe areas, wake lock, audio unlock.
*Done when:* installed from Safari on a real iPhone and from Chrome on a real
Android, both playable offline after install.

**WP8 — Design.** Bring the app into «Бумажки»: words on slips, the felt
background, Playfair for the word itself. The round screen is the one place the
design has to be *loud* — a word at 4rem and two enormous buttons.

**WP9 — Cutover.** The §4.2 edits: landing page, both `/android/*` pages, nav.
Plus the DESIGN.md amendment to the no-JS rule (§3).
*Done when:* no page offers the APK as the primary action, and every inbound
`/android/*` link still lands somewhere sensible.

**WP10 — Server (§8).** Game-id de-duplication and dictionary `Cache-Control`.
Independent of WP1–WP9 and can land first; WP6 should send the id from the
start so the two meet.

Rough sequencing: WP1–WP3 are the foundation and are worth doing in one pass;
WP4 is the bulk of the UI work; WP5–WP6 are small once WP4 exists. WP10 is an
afternoon and unblocks nothing, so do it whenever.

---

## 8. Server-side changes (WP10)

Two, both small.

### 8.1 De-duplicate uploads

The PWA sends a `game_id` (UUID, minted when the game starts, stable across
retries) in the v2 log. `/api/v2/game/log` keeps it as the `GameLog` entity's
key instead of an auto id, so a re-send is an idempotent overwrite and enqueues
no second stats task. An ambiguous network failure then becomes safe to retry,
which is what makes the outbox in §5.4 correct rather than hopeful.

`parse_log_v2` ignores unknown top-level keys, so old clients and new clients
can both post through the same handler; a log without an id keeps the current
behaviour.

That leaves the legacy installs of §0.2, which send no id and will keep
double-posting until they die out. If the duplicate rate turns out to matter,
the fallback is a content heuristic — same word list, same player count, start
timestamps within a minute — applied only to id-less logs. Not worth building
until the data says so.

**Care required:** this changes what goes into the rating pipeline. Rating is
cumulative and not recomputed, so a bug here corrupts word difficulties
permanently. The change wants its own test alongside
`tests/test_stats_datastore.py::test_pipeline_end_to_end`, asserting that
posting the same log twice moves a word's `E` exactly once.

### 8.2 Cache-Control on the dictionary

`_serve_dictionary` sets an ETag but no `Cache-Control`, so every revalidation
is a full conditional request. Add `max-age=3600, stale-while-revalidate` — the
ETag already makes a stale read safe, and the dictionary is regenerated on a
cron, not per request.

### Not doing

Word complaints stay dropped (§0.1). No accounts, no server-side game state.

---

## 9. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| iOS evicts storage after a week | high | `storage.persist()`, eviction detection, explicit test |
| Timer drift when the screen sleeps | high | wall-clock timers, never tick counting |
| Log rejected by `parse_log_v2` heuristics | medium | golden-log test in this repo's suite (WP6) |
| Dictionary grows past comfortable IndexedDB size | low | 1.3 MB today; bucketed records keep writes incremental |
| Service worker serves a stale shell after deploy | medium | version-stamped caches, update banner |
| Double-counted games from new clients | medium | accept 2xx; `game_id` (§8.1) |
| Double-counted games from retired installs | certain, decaying | §0.2 — accepted, heuristic held in reserve |
| Rating corrupted by the de-dup change | low, unrecoverable | dedicated test (§8.1); ratings are cumulative and never recomputed |
| Players lose game history at cutover | certain | accepted (§0.1) |

## 10. What this plan does not cover

Multiplayer over the network, accounts, the user's own word lists
(`UserDictionaryWord` — the legacy sync contracts still exist and could be
wired in later), languages other than `ru`, and any change to how difficulty is
computed. Game history and word complaints are deferred, not designed away —
see §0.1.

---

## 11. What building it turned up

Three things the plan could not have known, all of them found by running the
thing rather than reading it.

### 11.1 Failed words are counted nowhere

`parse_log_v2` fills `seen_words_time` only in its `'guessed'` branch, and the
pipeline iterates exactly that dict when calling `update_word`. So a word that
was an error, or that went back in the hat, is written to the log, shown to the
player on the verdict screen — and then never reaches a counter. It does not
even increment `used_times`.

The consequence is not local to the app: **`failed_times` can only ever have
been fed by v1 logs**, which no client has produced for years. The site's
«ошибкоопасные слова» table is therefore ranking on frozen history, and will
keep doing so no matter how many games the new app sends. Pinned by
`tests/test_pwa_log_contract.py::test_the_apps_log_survives_the_whole_pipeline`
so the day someone changes it, it is a decision rather than an accident.

Worth fixing separately — either by counting attempts in the parser, or by
retiring the table.

### 11.2 A worker at /play/sw.js cannot control /play

The obvious registration — scope `/play/` — installs cleanly, reports success,
and then controls nothing, because the document is at `/play` and a
trailing-slash scope does not cover it. The app would have looked fine and
simply never worked offline. It needs scope `/play` plus
`Service-Worker-Allowed: /play` from the server, both of which are now in
`app.yaml` with the reason written next to them.

### 11.3 Borrowing the stylesheet means borrowing its class names

`static/play/app.css` deliberately adds no colour and no type, only layout, so
that the app cannot drift from the site. The cost is a shared namespace: the
first version used `.tile__note`, which `hat.css` already defines for the
statistics pages in `--ink-muted` — a colour meant for dark felt, and
unreadable on a honey slip. The app's own classes are now named for what they
are (`.mode`, `.mode__name`), which is the discipline this arrangement asks
for in exchange for never having a second design.

### 11.4 A Back the app absorbs must be re-armed by a tap, not by popstate

Holding the reader inside a screen means putting a spare history entry above
the one they are on and pushing another after each Back spends one. Doing that
push from the `popstate` handler — the obvious place — is what breaks the app.
Chromium's [history manipulation intervention][hmi] stops honouring the
document's user activation once a same-document Back has happened, so a
`pushState` from the handler counts as one made without a gesture, and the
penalty is not aimed at the new entry: *every* same-document entry, the launch
entry included, is then marked skippable. The next Back skips all of them and
closes the installed app. It looked like "the countdown dismissal breaks Back",
because dismissing a countdown was the one place that re-armed without a tap
following it.

So entries are pushed only while a gesture is in hand — the countdown gets its
own entry when the tap starts it, and in-game spares are topped back up on the
next tap, which also clears any skippable mark. It follows that no app can trap
Back indefinitely without the reader touching the screen, which is the point of
the intervention; two spares in a game are what a phone being passed around can
absorb before a tap arrives.

[hmi]: https://chromium.googlesource.com/chromium/src/+/main/docs/history_manipulation_intervention.md

## 12. Before this goes to production

- Install from Safari on a real iPhone and from Chrome on a real Android, and
  play a full game offline on each. Everything else has been verified in
  headless Chrome, which is not the same thing — particularly for audio
  unlocking, the wake lock, and safe areas.
- Leave an installed copy untouched for a week and open it offline, to see
  whether `navigator.storage.persist()` actually held (§6). This is the most
  likely field failure and cannot be rushed.
- Watch the first real games arrive: a game whose words all came in under two
  seconds is discarded whole and silently (§2.1), which is exactly what a
  tester tapping through produces.
