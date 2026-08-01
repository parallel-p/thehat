# The Hat — Python 3 / Modern Google Cloud Migration Plan

Plan for an executor agent. Written 2026-08-01 after a full code inventory and production
analysis (30 days of request logs, Datastore kind stats, full 50,023-entity GameLog scan).
Follow work packages in order. Every claim about production behavior below was verified
against the live project on 2026-08-01.

---

## 1. Mission

Replace the Python 2.7 first-gen App Engine app (webapp2, deployed 2020, unmaintainable)
with a Python 3.12 FastAPI app deployed as a **new version of the same App Engine
`default` service in project `the-hat`**, preserving the URL `the-hat.appspot.com` and
byte-level API compatibility for two generations of shipped mobile clients. Port only the
live core; drop everything with zero production traffic (list in §4).

## 2. Fixed decisions (do not relitigate)

- **Target: App Engine standard, `runtime: python312`**, same project/service. NOT Cloud Run
  (URL is baked into shipped clients and only App Engine can serve it).
- **No bundled App Engine APIs.** Never set `app_engine_apis: true`. Use only:
  FastAPI, `google-cloud-ndb`, `google-cloud-tasks`, `google-cloud-storage`, `trueskill` (PyPI).
  This keeps a future Cloud Run exit open.
- **Database stays.** Firestore in Datastore mode, project `the-hat`, zero data migration.
  Old and new versions share it during cutover — that is intentional.
- **Framework: FastAPI** with gunicorn+uvicorn workers (works on GAE standard).
- Staging project **`the-hat-staging`** (already created, billing linked, App Engine app
  exists in `us-central`, hostname `the-hat-staging.uc.r.appspot.com`).
- User decisions (2026-08-01): v1 compat API is kept **indefinitely** (no sunset);
  statistics pages are kept **minimal with robots.txt bot-blocking**; **no** install-id
  analytics header (user counts not needed); cutover is a **gradual IP split** per WP8.
- User decisions (2026-08-01, round 2):
  - **No test writes to production, ever.** All write-path verification happens on
    staging against imported production data (WP5). Prod smoke tests (WP7) are
    read-only GETs. The first production writes are real client traffic at the WP8 split.
  - v1 compat scope confirmed = **game_log PUT + udict sync only**; all other legacy
    routes (results, save_game, complain, settings sync, pregame) return 404.
  - **No admin UI.** Curation is script-only (`scripts/` in the new layout).
  - Repo strategy confirmed: same repo, branch `migration/py3`, new layout at root,
    `MIGRATION_PLAN.md` as the branch's first commit.

## 3. Production ground truth (verified 2026-08-01)

- Traffic: 3,237 real requests/30d; ~200 games uploaded/month; ≈20 unique players/month.
- Live clients:
  1. **Flutter app** (`Dart/3.3`, `Dart/3.4` UAs): `POST /api/v2/game/log`,
     `GET /api/v2/dictionary/ru`. Log payload is format "2.0" (anonymous — no device id).
  2. **Legacy Java Android** (`Apache-HttpClient/UNAVAILABLE (java 1.4)` UA, 10 devices):
     `PUT /<device_id>/game_log/<game_id>`, `GET/POST /<device_id>/api/udict[...]`.
     Ancient TLS stack — do not tighten TLS/redirect/header behavior on these routes.
- Currently serving version: `20200514t133903` (Python 2.7). Version `3` (2014) is also
  SERVING with 0% traffic — decommission at the end.
- Prod cron today: 3 jobs; `/cron/notifications/update` has failed 405 daily for years
  (Channel API removed); the other two feed pages only bots read. None survive.
- Datastore: 665 MB, dominated by `GameLog` (50k). Kinds with near-zero rows
  (PreGame=13, PinNumber=2, Function=1, CurrentGame=1) belong to dropped modules.
- IAM: nzinov@gmail.com is Owner on `the-hat`; Sashkent3@gmail.com is Editor (active
  collaborator — keep informed). `the-hat-dev` is NOT usable (owners unreachable, no billing).

## 4. Scope

### Port (the live core)
| Module | Old code (read it before porting) |
|---|---|
| v2 game-log ingest | `handlers/log_saving.py` `GameLog2Handler` |
| v2 dictionary serving | `handlers/global_dictionary/words.py` `DictionaryHandler`, `ListDictionaries` |
| v1 game-log compat | `handlers/log_saving.py` `GameLogHandler` |
| v1 user-dictionary compat | `handlers/user_dictionary.py` `UserDictionaryHandler`; `objects/user_devices.py` |
| Stats pipeline (TrueSkill) | `handlers/statistics/calculation.py` `AddGameHandler`; `environment.py`; vendored `trueskill/` → PyPI `trueskill` |
| Dictionary generation job | `handlers/global_dictionary/words.py` `GenerateDictionary` |
| Landing + static + TOS | `app.yaml` static handlers, `templates/landing.html`, `assets/`, `tos/` |
| Word/total statistics pages (simplified) | `handlers/statistics/word.py`, `total.py` — reimplement minimally, no memcache, no plots |

### Drop (verified zero traffic and/or broken/unsafe — do NOT port)
Pregame lobby + PIN numbers, settings sync API (`user_properies.py`), word
streams/packages + their admin, complaints admin + API, unknown-words admin, frequency
dictionary, word lookup admin, newsfeed (hardcoded password `123456`), Channel API
notifications (incl. the token injection in `handlers/__init__.py:draw_page` and the
`goog.appengine.Channel` block in `templates/base.html`), matplotlib plot rendering,
function-statistics (`exec()` of Datastore-stored code — security hole), link-device,
remove-duplicates, game results endpoints (`GameResultsHandler` etc. — zero traffic),
save_game, web game creation, all 15 admin pages, appstats, remote_api, legacy
`/admin_panel`. Vendored `babel/`, `pytz/`, `lib/cloudstorage/`, `trueskill/` trees die
with them.

### Datastore models needed (port to `google-cloud-ndb`, keep kind & property names EXACTLY)
`GameLog`, `GlobalDictionaryWord`, `WordLookup`, `Dictionary` (from
`objects/global_dictionary.py`, `objects/game_results_log.py`), `User`, `Device`,
`OwnedModel` query helper (`objects/user_devices.py` — replace `ndb.UserProperty` field:
keep reading existing entities but never write that property; model it as a generic
property or omit), `UserDictionaryWord`, `UnknownWord`, `DailyStatistics`,
`TotalStatistics`, `GamesForPlayerCount`, `GameLength`, `StatisticVersion`,
`EnumProperty` (`objects/enum_property.py`) or replace with plain IntegerProperty
(wire-compatible). Composite indexes to keep in `index.yaml`:
`UserDictionaryWord(owner, version asc)`, `UserDictionaryWord(owner, version desc)`,
`GlobalDictionaryWord(deleted, lang, E)`.

## 5. API compatibility contracts (byte-level; verified from code)

Golden rule: when in doubt, diff against the live prod endpoint (GETs are safe to call).

1. **`POST /api/v2/game/log`** — body: raw JSON (do not validate schema beyond
   parseability; store raw body string in `GameLog.json`, auto-id key, `time=now`).
   Enqueue stats task with the entity's urlsafe key, ~5 s delay. Respond **202, empty body**.
2. **`GET /api/v2/dictionary/{lang}`** (and bare `/api/v2/dictionary` → lang "ru") —
   stream the GCS object referenced by `Dictionary(id=lang).gcs_key`. Set `ETag`; honor
   `If-None-Match` → **304**. 404 for unknown lang. Prod bucket: `the-hat.appspot.com`,
   objects under `/dictionary/<timestamp>`.
3. **`GET /api/v2/dictionaries`** — replicate the JSON produced by `ListDictionaries`
   (read the old handler; verify against `curl https://the-hat.appspot.com/api/v2/dictionaries`).
4. **`PUT /{device_id}/game_log/{game_id}`** and **`PUT /{device_id}/game_log`** —
   game id comes from **body** `setup.meta["game.id"]`, NOT the URL. Idempotent:
   if `GameLog` with that string id exists, do nothing. Else create
   `GameLog(id=game_id, json=body)` and enqueue stats task. Respond **201** always.
   Auth: device id from URL or `TheHat-Device-Identity` header; unknown devices are
   auto-created (see `get_device_and_user` — creates on read).
5. **`GET /{device_id}/api/udict`** and **`.../api/udict/since/{version}`** — compute
   `version` = max `UserDictionaryWord.version` over owner ∈ {user, all linked devices}
   (see `OwnedModel.query` fan-out); return
   `{"version": N, "words": [entity.to_dict(exclude=('owner',))]}` where words have
   `version > since` (0 for bare route). Match old ndb `to_dict()` serialization of the
   `added` DateTimeProperty exactly — verify by diffing staging vs prod with seeded data.
6. **`POST /{device_id}/api/udict/`** — changes arrive as **form field `json`**
   (application/x-www-form-urlencoded), a JSON array of `{word, status, ...}` dicts.
   Upsert each by word with a single incremented version; response body is the **bare
   version integer** (no JSON wrapper).
7. **Stats task target `POST /internal/add_game_to_statistic`** (Cloud Tasks; param
   `game_key`, form-encoded, matching old `taskqueue.add(params=...)`). Port the logic of
   `AddGameHandler` faithfully: v1/v2 log parsing, per-word TrueSkill update
   (`environment.py` parameters: mu=50, sigma=50/3, beta=50/6, tau=50/300,
   draw_probability=0), writes to `GlobalDictionaryWord`, `UnknownWord`,
   `DailyStatistics`, `TotalStatistics`, `GamesForPlayerCount`, `GameLength`. Use
   `google-cloud-ndb` transactions where the old code used `@ndb.transactional`. Restrict
   the route: require `X-AppEngine-QueueName` header (App Engine strips it from external
   requests; Cloud Tasks App Engine targets set it) — this replaces `login: admin`.
8. **Static/web**: `/` and `/landing` → landing page; `/assets/*`, `/tos/*`,
   `/favicon.ico`, `/android/beta`, `/android/new/beta` as today. NEW: serve
   `/robots.txt` with `Disallow: /statistics/` (kills the 3.8k/mo bot crawl).
   `/statistics/word_statistics` and `/statistics/total_statistics`: minimal server-side
   pages reading the same kinds; no memcache (in-process TTL dict is fine), no images.
9. **Everything else returns 404/410.** Dropped routes must not 500.

## 6. New repo layout (branch `migration/py3`)

```
app.yaml            # runtime: python312, entrypoint: gunicorn -k uvicorn.workers.UvicornWorker app.main:app
requirements.txt    # fastapi, gunicorn, uvicorn, google-cloud-ndb, google-cloud-tasks,
                    # google-cloud-storage, trueskill, jinja2
index.yaml          # 3 composite indexes from §4
cron.yaml           # empty `cron:` list (deployed only at cutover)
app/
  main.py           # FastAPI app, routes
  models.py         # ndb models (§4)
  api_v2.py         # contracts 1–3
  api_v1_compat.py  # contracts 4–6
  stats.py          # contract 7 (parser + trueskill)
  dictionary_gen.py # admin job (§7 WP6)
  web.py            # contract 8
  tasks.py          # Cloud Tasks enqueue helper (queue: logs-processing, location us-central1)
scripts/            # curation utilities (add words, regenerate dictionary) — replaces all admin UI
static/ templates/  # landing, tos, assets carried over
tests/              # new pytest suite (Datastore emulator)
legacy/             # (optional) old handlers kept for reference, excluded from deploy
```

## 7. Work packages, in order

**WP0 — Safety net.** `gcloud datastore export gs://the-hat-backup-20260801/pre-migration --project the-hat`
(create the bucket in `the-hat` first, region us-central1). Copy the current dictionary
objects: `gsutil ls gs://the-hat.appspot.com/dictionary/`. Do not proceed without a
successful export.

**WP1 — Scaffold.** Branch `migration/py3`, layout per §6, health endpoint, deploy to
staging (`gcloud app deploy --project the-hat-staging`) to prove the pipeline early.

**WP2 — Models + contracts 1–6.** Port models, implement API. Unit tests against the
Datastore emulator (`gcloud emulators firestore start --database-mode=datastore-mode`).
The old testbed suite in `tests/` is reference material only — port assertions, not code.

**WP3 — Stats pipeline (contract 7).** Read `handlers/statistics/calculation.py` fully
first (431 lines; note `@ndb.transactional(xg=True)` blocks and the v1/v2 parser split).
Golden test: take 20 real GameLog payloads (varied: flutter-v2 + legacy-setup formats),
run old-code math by hand-derived fixtures, assert new code produces identical E/D
updates to 1e-9. Create the Cloud Tasks queue in both projects:
`gcloud tasks queues create logs-processing --location us-central1 --project <p>`.

**WP4 — Web pages (contract 8).**

**WP5 — Staging full rehearsal.** Import the WP0 export into staging
(`gcloud datastore import --project the-hat-staging`; grant staging's service agent
Storage Object Viewer on the backup bucket). Copy dictionary blobs to
`gs://the-hat-staging.appspot.com/`. Then:
- Replay the last 30 days of real game-log payloads (pull them from prod Datastore
  read-only; a pager script exists — see `scan_gamelogs.py` pattern in the session
  scratchpad) against staging; verify one stats task per log runs clean and
  `GlobalDictionaryWord` deltas match prod's values for the same games.
- Smoke every contract with curl using the real client User-Agents (Dart + Apache-HttpClient).
- Load index.yaml (`gcloud app deploy index.yaml --project the-hat-staging`) and confirm
  udict queries don't need missing indexes.

**WP6 — Dictionary generation.** Port `GenerateDictionary` as an authenticated admin-only
endpoint or a one-off script (`python -m app.dictionary_gen`). Verify output blob is
byte-identical in format to the current `/api/v2/dictionary/ru` response.

**WP7 — Prod deploy, no traffic.** `gcloud app deploy --project the-hat --no-promote --version py3`.
Deploy `index.yaml` to prod (additive — safe). Smoke test on
`https://py3-dot-the-hat.appspot.com` — **read-only GETs only** (dictionary, dictionaries
list, stats pages, landing, robots.txt, 404s on dropped routes). Do NOT exercise write
endpoints against prod — write paths must already be fully proven on staging in WP5.
The first production writes are real client traffic during the WP8 split; watch them
closely there.

**WP8 — Cutover.** `gcloud app services set-traffic default --splits py3=.1,20200514t133903=.9 --split-by ip --project the-hat`.
Watch `gcloud app logs tail` + error counts for 24 h; the signals that matter: 201s on
legacy PUTs from the Java UA, 202s from Dart UA, stats tasks completing. Then 100%.
Deploy the empty `cron.yaml` to prod now (removes the 3 legacy jobs). **Rollback at any
point:** `gcloud app services set-traffic default --splits 20200514t133903=1 --project the-hat`.

**WP9 — Decommission (after ≥2 weeks stable).** Stop version `3` (2014) and
`20200514t133903`; keep them undeleted for another month, then delete. Legacy push queues
die with the old version (Cloud Tasks queue `logs-processing` replaces them). Dead-kind
cleanup (PreGame, PinNumber, Function, WordFrequency, `_GAE_MR_*`, GameHistory…) is a
separate future task — requires a fresh export first and explicit user sign-off.

## 8. Guardrails for the executor

- **Prod Datastore is read-only for the executor.** The only writes ever made to prod
  come from real client traffic served by the promoted app (WP8 onward). No test
  entities, no bulk deletes, no bulk updates, no "cleanup" — ever.
- Do not deploy `cron.yaml` or `queue.yaml` to prod before WP8. Deploying the app itself
  with `--no-promote` is safe.
- Do not add `secure: always`, HSTS, or strict request validation on contract 4–6 routes
  (the Java 1.4-era client cannot be updated or tested).
- Do not use `app_engine_apis: true` or any `google.appengine.*` import.
- Do not delete or stop any prod version until WP9, and only with user confirmation.
- Kind names, property names, and index definitions must match the old code exactly —
  the old version keeps reading the same data during the traffic split.
- If a contract detail is ambiguous, the live prod response is the specification.
- Anything failing in staging blocks promotion; there is no "fix forward on prod".

## 9. Environment reference

| | prod | staging |
|---|---|---|
| project | `the-hat` | `the-hat-staging` |
| hostname | the-hat.appspot.com | the-hat-staging.uc.r.appspot.com |
| region | us-central | us-central |
| database | Firestore/Datastore mode, 665 MB live | empty; import WP0 export |
| default GCS bucket | the-hat.appspot.com | the-hat-staging.appspot.com |
| billing | revolut (01603D-4FEB67-88DB92) | same |
| current versions | `20200514t133903` (100%), `3` (0%) | none yet |

Auth: `gcloud` on this machine is authenticated as nzinov@gmail.com (Owner on both).
APIs enabled on staging: App Engine, Datastore, Cloud Tasks, Cloud Build, Logging, Storage.
