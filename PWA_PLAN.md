# Шляпа as a PWA — plan

Recreating [beret](https://github.com/nzinov/beret) — the Flutter app currently
advertised at `/android/new/beta` — as an offline-capable web app served from
this repo, installable on both Android and iOS.

Branch: `pwa/plan`, cut from `migration/py3`.

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
  python3 migration (`app/main.py` header). The PWA should either drop the
  feature or we re-add a handler — see §8.

---

## 2. Server contracts the PWA depends on

| Endpoint | Used for | Status |
|---|---|---|
| `GET /api/v2/dictionary/ru` | word list | exists, ETag-cached (`app/api_v2.py`) |
| `GET /api/v2/dictionaries` | language list | exists |
| `POST /api/v2/game/log` | game upload → 202 | exists |
| `POST /{deviceId}/complain` | word complaints | **gone** |

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

## 3. The build-vs-rewrite decision

**Option A — `flutter build web` and host the output.** Beret already has a
`web/` target. Fastest path to parity.

Against it: the CanvasKit bundle is ~2 MB before the app's own code (the HTML
renderer is smaller but its text rendering is poor for Cyrillic); it paints to a
canvas, so no text selection, no real accessibility, and a "not-a-web-page"
feel; it drags a Flutter SDK into a repo whose whole stated discipline is *no
CDN, no third-party request, no build step*; and it would look nothing like the
rest of the site, which now has a deliberate design language. iOS PWA quirks
(audio unlock, wake lock, storage eviction) still have to be solved by hand
inside a framework that hides the platform from you.

**Option B — write it as a small vanilla PWA.** ~1 500–2 000 lines of plain ES
modules, the site's own CSS tokens, no framework, no bundler. First load is well
under 100 KB plus the dictionary.

**Recommendation: Option B.** The app is a state machine, six screens and a
timer — the part that is genuinely hard (offline storage, the log contract, iOS
behaviour) is identical either way, and Option A pays 2 MB and a toolchain for
the easy part. It also keeps the promise the rest of the site makes.

One thing to state plainly: **this introduces JavaScript to a codebase that
currently has none**, and DESIGN.md says so as a rule. That rule is about the
marketing and statistics pages, which must render as documents. An app that
runs a stopwatch is a different thing, and the rule should be amended rather
than quietly broken — the pages stay no-JS, `/play` is allowed script.

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

The landing page's «Скачать приложение» becomes «Играть» → `/play`, with the
APK kept as a secondary link.

**Open question:** the app currently talks to `the-hat.appspot.com` while the
site links to `thehat.ru`. The PWA must be same-origin with the API or the
service worker cannot cache it cleanly. Confirm which hostname serves this App
Engine app before WP1.

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
verdict, round editing, scoreboard, history.
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

**WP9 — Cutover.** Landing page points at `/play`; `/android/new/beta` keeps the
APK; a note in DESIGN.md amending the no-JS rule (§3).

Rough sequencing: WP1–WP3 are the foundation and are worth doing in one pass;
WP4 is the bulk of the UI work; WP5–WP6 are small once WP4 exists.

---

## 8. Server-side changes this needs

Small, and each is optional-but-recommended:

1. **De-duplicate uploads.** Accept a client `game_id` (UUID) on
   `/api/v2/game/log` and skip an already-seen id. Without it, an ambiguous
   network failure double-counts a game — which, per §1.6, is probably already
   happening today with beret.
2. **Complaints.** Either restore a minimal `POST /api/v2/word/complain`
   (device id, word, reason) writing to `UnknownWord`-style storage, or drop the
   button. Recommendation: restore it — word vetting is what keeps the
   dictionary honest, and the button is one line in the UI.
3. **`Cache-Control` on the dictionary.** It is served with an ETag but no
   max-age; a short max-age plus the ETag makes the revalidation cheap.
4. Nothing else. The PWA is a client of contracts that already exist.

---

## 9. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| iOS evicts storage after a week | high | `storage.persist()`, eviction detection, explicit test |
| Timer drift when the screen sleeps | high | wall-clock timers, never tick counting |
| Log rejected by `parse_log_v2` heuristics | medium | golden-log test in this repo's suite (WP6) |
| Dictionary grows past comfortable IndexedDB size | low | 1.3 MB today; bucketed records keep writes incremental |
| Service worker serves a stale shell after deploy | medium | version-stamped caches, update banner |
| Double-counted games | already happening | accept 2xx; add `game_id` (§8.1) |

## 10. What this plan does not cover

Multiplayer over the network, accounts, the user's own word lists
(`UserDictionaryWord` — the legacy sync contracts still exist and could be
wired in later), languages other than `ru`, and any change to how difficulty is
computed.
