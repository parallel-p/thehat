# The Hat — server

Python 3.12 / FastAPI application for the Hat word game, running on App Engine
standard in project `the-hat` (`the-hat.appspot.com`).

## Layout

```
app/                FastAPI application
  main.py           routing
  models.py         Datastore models (google-cloud-ndb)
  api_v2.py         current Flutter client API
  api_v1_compat.py  legacy Java Android client API
  stats.py          TrueSkill word-rating pipeline
  py2compat.py      CPython 2.7 semantics the pipeline depends on
  dictionary_gen.py dictionary blob generation job
  web.py            landing page + statistics pages
scripts/            maintenance jobs (there is no admin UI)
tests/              pytest suite; runs against the Datastore emulator
legacy/             the python27 application, for reference only; not deployed
```

## Development

```bash
make venv
make emulator            # in a second shell
make test
make serve               # http://localhost:8080
```

## Tests

The statistics pipeline is pinned to the python27 implementation by a golden
test: `tests/py2_reference/run_reference.py` executes the *original*
`legacy/handlers/statistics/calculation.py` under python 2.7 and records what it
writes; `tests/test_stats_golden.py` replays the same logs through `app.stats`
and requires identical traces.

The committed fixtures are synthetic. The production-derived ones are gitignored
(they contain real player names and this repository is public); regenerate them
with read-only access to production:

```bash
make fixtures            # export prod logs + word ratings
make golden              # needs python 2.7 at $(PY27)
make test
```

## Deployment

```bash
make queue-staging indexes-staging deploy-staging
make deploy-prod-noserve # WP7: deploy to prod without taking traffic
```

## Curation

There is no admin UI; curation is script-only.

```bash
python -m scripts.add_words --project the-hat --file words/new.txt
python -m app.dictionary_gen         # publish a new dictionary blob
```

See `MIGRATION_PLAN.md` for the work packages and API compatibility contracts,
and `MIGRATION_NOTES.md` for what the port actually did — in particular the
legacy bugs that are preserved deliberately.

## Localization

The python27 app used Jinja2 i18n with `{% trans %}` tags and `.po` catalogs in
`legacy/locale/`. The py3 app serves only the landing page and two statistics
pages, all Russian-only, so the i18n machinery was not carried over.
