"""Pytest fixtures backed by the Cloud Datastore emulator.

Start it with::

    gcloud beta emulators datastore start --project=the-hat-test \\
        --host-port=localhost:8432 --no-store-on-disk --consistency=1.0

``make test`` does this for you.
"""

import os

import pytest

os.environ.setdefault("DATASTORE_EMULATOR_HOST", "localhost:8432")
os.environ.setdefault("DATASTORE_PROJECT_ID", "the-hat-test")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "the-hat-test")
os.environ.setdefault("DATASTORE_DATASET", "the-hat-test")
os.environ.setdefault("TASKS_DISABLED", "1")
# Nothing here may ever talk to real Google infrastructure.
os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)


KINDS = [
    "User", "Device", "UserDictionaryWord", "GlobalDictionaryWord", "WordLookup",
    "Dictionary", "GameLog", "UnknownWord", "DailyStatistics", "TotalStatistics",
    "GamesForPlayerCount", "GameLength", "StatisticVersion", "WordFrequency",
    # The statistics pages' shared cache. Without it here one test's numbers
    # are served to the next from Datastore, which the in-process cache being
    # cleared below no longer prevents.
    "StatsCache",
]


@pytest.fixture(scope="session")
def ndb_client():
    from app.ndb_ctx import client

    return client()


@pytest.fixture
def ndb_context(ndb_client):
    """A clean datastore and an active ndb context for one test.

    The app opens its own context per request (in the TestClient's portal
    thread); this one is for setting entities up and asserting on them.
    """
    from google.cloud import ndb

    with ndb_client.context(cache_policy=lambda key: False) as context:
        for kind in KINDS:
            keys = ndb.Query(kind=kind).fetch(keys_only=True)
            if keys:
                ndb.delete_multi(keys)
        yield context


@pytest.fixture(autouse=True)
def clear_page_cache():
    """Drop the statistics pages' in-process TTL cache between tests.

    It replaces the old memcache and is keyed globally with a one-hour TTL, so
    without this one test's data leaks into the next one's assertions.
    """
    from app import web

    web._cache.clear()
    yield
    web._cache.clear()


@pytest.fixture
def client(ndb_context):
    from starlette.testclient import TestClient

    import app.main as main_module

    with TestClient(main_module.app) as test_client:
        yield test_client
