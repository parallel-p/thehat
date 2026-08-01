VENV ?= .venv
PY := $(VENV)/bin/python
PY27 ?= $(HOME)/.pyenv/versions/2.7.18/bin/python
EMULATOR_HOST ?= localhost:8432
STAGING ?= the-hat-staging
PROD ?= the-hat

.PHONY: help venv emulator test serve deploy-staging deploy-prod-noserve \
        golden fixtures indexes-staging queue-staging queue-prod clean \
        smoke-staging smoke-prod

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "%-22s %s\n", $$1, $$2}'

venv: ## Create the virtualenv and install requirements
	python3.12 -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt -r requirements-dev.txt

emulator: ## Run the Datastore emulator in the foreground
	gcloud beta emulators datastore start --project=the-hat-test \
		--host-port=$(EMULATOR_HOST) --no-store-on-disk --consistency=1.0

test: ## Run the test suite (needs `make emulator` in another shell)
	DATASTORE_EMULATOR_HOST=$(EMULATOR_HOST) $(PY) -m pytest tests -q

serve: ## Run the app locally against the emulator
	DATASTORE_EMULATOR_HOST=$(EMULATOR_HOST) GOOGLE_CLOUD_PROJECT=the-hat-test \
		TASKS_DISABLED=1 $(VENV)/bin/uvicorn app.main:app --reload --port 8080

# -- WP3 golden fixtures ----------------------------------------------------
# Regenerating requires python 2.7 and read access to production Datastore.
# The generated files are committed; regenerate only when the reference
# implementation itself is in question.

fixtures: ## Re-export production fixtures (read-only)
	$(PY) -m scripts.export_prod_logs --project $(PROD) --recent --limit 300 \
		--out tests/fixtures/prod_logs.jsonl
	$(PY) -m scripts.build_word_table --logs tests/fixtures/prod_logs.jsonl \
		--out tests/fixtures/word_ratings_prod.json
	$(PY) scripts/make_test_logs.py --out tests/fixtures/synthetic_logs.jsonl \
		--words-out tests/fixtures/word_ratings.json

golden: ## Regenerate golden traces by running the python27 code under python 2.7
	$(PY27) tests/py2_reference/run_reference.py \
		--logs tests/fixtures/synthetic_logs.jsonl \
		--words tests/fixtures/word_ratings.json \
		--out tests/fixtures/stats_golden_synthetic.jsonl
	$(PY27) tests/py2_reference/run_reference.py \
		--logs tests/fixtures/prod_logs.jsonl \
		--words tests/fixtures/word_ratings_prod.json \
		--out tests/fixtures/stats_golden_prod.jsonl
	$(PY27) tests/py2_reference/dump_dict_orders.py \
		> tests/fixtures/py2_dict_orders.json

# -- deployment -------------------------------------------------------------

queue-staging: ## Create the Cloud Tasks queue on staging
	gcloud tasks queues create logs-processing --location us-central1 \
		--project $(STAGING) --max-attempts 2 --max-dispatches-per-second 3 \
		--max-concurrent-dispatches 5 || true

queue-prod: ## Create the Cloud Tasks queue on production
	gcloud tasks queues create logs-processing --location us-central1 \
		--project $(PROD) --max-attempts 2 --max-dispatches-per-second 3 \
		--max-concurrent-dispatches 5 || true

indexes-staging: ## Deploy composite indexes to staging
	gcloud app deploy index.yaml --project $(STAGING) --quiet

deploy-staging: ## Deploy the app to staging
	gcloud app deploy app.yaml --project $(STAGING) --quiet

deploy-prod-noserve: ## WP7: deploy to production without taking traffic
	gcloud app deploy app.yaml --project $(PROD) --no-promote --version py3 --quiet

smoke-staging: ## Smoke every contract against staging (includes write paths)
	$(PY) -m scripts.smoke --target https://the-hat-staging.uc.r.appspot.com

smoke-prod: ## WP7: read-only smoke against the un-promoted production version
	$(PY) -m scripts.smoke --target https://py3-dot-$(PROD).appspot.com --read-only

clean:
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
	rm -rf .pytest_cache
