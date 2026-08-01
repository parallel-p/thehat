# -*- coding: utf-8 -*-
"""Contracts 1-3 of MIGRATION_PLAN.md §5."""

import json

import pytest

from app.models import Dictionary, GameLog


def test_game_log_upload_returns_202_with_empty_body(client, ndb_context, monkeypatch):
    enqueued = []
    monkeypatch.setattr("app.tasks.enqueue_stats_task",
                        lambda key, countdown=None: enqueued.append(key))

    payload = '{"version": "2.0", "attempts": []}'
    response = client.post("/api/v2/game/log", content=payload.encode("utf-8"))

    assert response.status_code == 202
    assert response.content == b""
    assert response.headers["content-type"] == "text/html; charset=utf-8"

    logs = GameLog.query().fetch()
    assert len(logs) == 1
    # Stored verbatim, and with an auto-assigned numeric id.
    assert logs[0].json == payload
    assert isinstance(logs[0].key.id(), int)
    assert logs[0].time is None
    assert len(enqueued) == 1


def test_game_log_upload_preserves_non_ascii_bytes(client, ndb_context, monkeypatch):
    monkeypatch.setattr("app.tasks.enqueue_stats_task", lambda key, countdown=None: None)
    payload = json.dumps({"version": "2.0", "attempts": [], "note": "шляпа"},
                         ensure_ascii=False)
    client.post("/api/v2/game/log", content=payload.encode("utf-8"))
    assert GameLog.query().fetch()[0].json == payload


def test_game_log_with_an_id_is_stored_once(client, ndb_context, monkeypatch):
    """A retried upload must not rate the game a second time.

    Ratings are cumulative and never recomputed, so a game counted twice moves
    every word in it twice and nothing later puts it back.
    """
    enqueued = []
    monkeypatch.setattr("app.tasks.enqueue_stats_task",
                        lambda key, countdown=None: enqueued.append(key))

    payload = json.dumps({"version": "2.0", "game_id": "b3f0-RETRY-0001",
                          "attempts": []})
    first = client.post("/api/v2/game/log", content=payload.encode("utf-8"))
    second = client.post("/api/v2/game/log", content=payload.encode("utf-8"))

    # The client cannot tell the two apart, and must not need to.
    assert first.status_code == second.status_code == 202
    logs = GameLog.query().fetch()
    assert len(logs) == 1
    assert logs[0].key.id() == "b3f0-RETRY-0001"
    assert len(enqueued) == 1


def test_a_retried_upload_moves_a_rating_only_once(client, ndb_context,
                                                   monkeypatch):
    """The same thing again, but measured where it actually matters."""
    from app import stats
    from app.models import Dictionary as DictionaryModel, GlobalDictionaryWord

    for word in ["кот", "дом", "мост", "лес"]:
        GlobalDictionaryWord(id=word, word=word, E=50.0, D=16.0, lang="ru").put()
    DictionaryModel(id="ru").put()

    keys = []
    monkeypatch.setattr("app.tasks.enqueue_stats_task",
                        lambda key, countdown=None: keys.append(key))
    payload = json.dumps({
        "version": "2.0", "game_id": "0000-ONCE-0000",
        "start_timestamp": 1700000000000, "end_timestamp": 1700001800000,
        "time_zone_offset": 0,
        "attempts": [
            {"word": w, "from": i % 2, "to": (i + 1) % 2,
             "time": 6000 + i * 2000, "extra_time": 0, "outcome": "guessed"}
            for i, w in enumerate(["кот", "дом", "мост", "лес"])],
    })
    client.post("/api/v2/game/log", content=payload.encode("utf-8"))
    client.post("/api/v2/game/log", content=payload.encode("utf-8"))
    assert len(keys) == 1

    from google.cloud import ndb
    assert stats.add_game_to_statistic(ndb.Key(urlsafe=keys[0])) == "ok"
    once = {w.word: w.E for w in GlobalDictionaryWord.query().fetch()}
    assert all(count == 1
               for count in (w.used_times
                             for w in GlobalDictionaryWord.query().fetch()))
    assert any(abs(e - 50.0) > 1e-6 for e in once.values())


def test_game_log_ignores_an_unusable_id(client, ndb_context, monkeypatch):
    """A malformed id loses de-duplication, never the game."""
    monkeypatch.setattr("app.tasks.enqueue_stats_task",
                        lambda key, countdown=None: None)
    for bad in ('{"game_id": "../../etc", "attempts": []}',
                '{"game_id": 17, "attempts": []}',
                '{"game_id": "", "attempts": []}',
                'not json at all'):
        client.post("/api/v2/game/log", content=bad.encode("utf-8"))
    logs = GameLog.query().fetch()
    assert len(logs) == 4
    assert all(isinstance(log.key.id(), int) for log in logs)


def test_dictionary_may_be_held_for_an_hour(client, ndb_context, monkeypatch):
    Dictionary(id="ru", gcs_key="abc").put()
    monkeypatch.setattr("app.api_v2.read_dictionary_blob", lambda key: b"[]")
    response = client.get("/api/v2/dictionary/ru")
    assert response.status_code == 200
    assert "max-age=3600" in response.headers["cache-control"]
    assert response.headers["etag"] == '"abc"'


def test_dictionaries_list(client, ndb_context):
    Dictionary(id="ru", gcs_key="123").put()
    response = client.get("/api/v2/dictionaries")
    assert response.status_code == 200
    assert response.content == b'["ru"]'
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert response.headers["cache-control"] == "no-cache"


def test_dictionary_unknown_lang_is_404(client, ndb_context):
    assert client.get("/api/v2/dictionary/xx").status_code == 404


def test_dictionary_serves_blob_and_sets_etag(client, ndb_context, monkeypatch):
    Dictionary(id="ru", gcs_key="1564137725").put()
    monkeypatch.setattr("app.api_v2.read_dictionary_blob", lambda key: b"[1,2,3]")

    response = client.get("/api/v2/dictionary/ru")
    assert response.status_code == 200
    assert response.content == b"[1,2,3]"
    assert response.headers["etag"] == '"1564137725"'


def test_bare_dictionary_route_defaults_to_ru(client, ndb_context, monkeypatch):
    Dictionary(id="ru", gcs_key="k").put()
    monkeypatch.setattr("app.api_v2.read_dictionary_blob", lambda key: b"ru-body")
    assert client.get("/api/v2/dictionary").content == b"ru-body"


def test_dictionary_honours_if_none_match(client, ndb_context, monkeypatch):
    Dictionary(id="ru", gcs_key="1564137725").put()
    monkeypatch.setattr("app.api_v2.read_dictionary_blob", lambda key: b"[1,2,3]")

    response = client.get("/api/v2/dictionary/ru",
                          headers={"If-None-Match": '"1564137725"'})
    assert response.status_code == 304
    assert response.content == b""
    # Production returns no ETag on a 304 (the old handler returned early).
    assert "etag" not in response.headers

    stale = client.get("/api/v2/dictionary/ru",
                       headers={"If-None-Match": '"999"'})
    assert stale.status_code == 200


@pytest.mark.parametrize("header,key,expected", [
    ('"abc"', "abc", True),
    ("abc", "abc", True),
    ('W/"abc"', "abc", True),
    ('"x", "abc"', "abc", True),
    ("*", "abc", True),
    ('"abd"', "abc", False),
    (None, "abc", False),
    ('"abc"', None, False),
])
def test_etag_matching(header, key, expected):
    from app.api_v2 import etag_matches

    assert etag_matches(header, key) is expected
