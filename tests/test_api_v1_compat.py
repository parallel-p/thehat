# -*- coding: utf-8 -*-
"""Contracts 4-6 of MIGRATION_PLAN.md §5 -- the legacy Java Android client.

Assertions ported from the python27 testbed suite (legacy/tests/userdictionary_test.py,
legacy/tests/log_handling_test.py); none of the old code is reused.
"""

import json

import pytest
from google.cloud import ndb

from app.models import Device, GameLog, User, UserDictionaryWord


@pytest.fixture
def no_tasks(monkeypatch):
    enqueued = []
    monkeypatch.setattr("app.tasks.enqueue_stats_task",
                        lambda key, countdown=None: enqueued.append(key))
    return enqueued


def game_body(game_id, extra=None):
    body = {"setup": {"meta": {"game.id": game_id}, "type": "hat", "words": []},
            "events": []}
    if extra:
        body.update(extra)
    return json.dumps(body)


# --------------------------------------------------------------------------
# Contract 4
# --------------------------------------------------------------------------


def test_put_game_log_creates_entity_keyed_by_body_game_id(client, ndb_context, no_tasks):
    body = game_body("game-42")
    response = client.put("/dev1/game_log/ignored-url-id", content=body.encode())

    assert response.status_code == 201
    assert response.content == b""
    log = GameLog.get_by_id("game-42")
    assert log is not None
    assert log.json == body
    assert no_tasks == [log.key.urlsafe().decode()]


def test_put_game_log_without_url_game_id(client, ndb_context, no_tasks):
    response = client.put("/dev1/game_log", content=game_body("game-7").encode())
    assert response.status_code == 201
    assert GameLog.get_by_id("game-7") is not None


def test_put_game_log_is_idempotent(client, ndb_context, no_tasks):
    body = game_body("dup")
    assert client.put("/dev1/game_log/dup", content=body.encode()).status_code == 201
    second = client.put("/dev1/game_log/dup",
                        content=game_body("dup", {"changed": True}).encode())
    assert second.status_code == 201

    assert len(GameLog.query().fetch()) == 1
    # The second upload must not have overwritten the stored payload...
    assert GameLog.get_by_id("dup").json == body
    # ...nor enqueued a second statistics task.
    assert len(no_tasks) == 1


def test_put_game_log_autocreates_unknown_device(client, ndb_context, no_tasks):
    client.put("/brand-new-device/game_log", content=game_body("g1").encode())
    devices = Device.query().fetch()
    assert [d.device_id for d in devices] == ["brand-new-device"]


def test_put_game_log_accepts_device_identity_header(client, ndb_context, no_tasks):
    client.put("/urldevice/game_log",
               content=game_body("g2").encode(),
               headers={"TheHat-Device-Identity": "headerdevice"})
    # The URL id wins when both are present, as in the old dispatch().
    assert [d.device_id for d in Device.query().fetch()] == ["urldevice"]


# --------------------------------------------------------------------------
# Contracts 5 and 6
# --------------------------------------------------------------------------


def test_udict_post_returns_bare_incrementing_version(client, ndb_context):
    requests = [
        '[{"word": "hat", "status": "ok"}, {"word": "rat", "status": "deleted"}]',
        '[{"word": "rat", "status": "deleted"}, {"word": "drop", "status": "deleted"}]',
    ]
    for expected_version, payload in enumerate(requests, start=1):
        response = client.post("/123/api/udict", data={"json": payload})
        assert response.status_code == 200
        assert response.text == str(expected_version)
        assert response.headers["content-type"] == "text/html; charset=utf-8"

    words = {w.word: w.version for w in _all_udict_words()}
    assert words == {"hat": 1, "rat": 2, "drop": 2}


def test_udict_post_with_trailing_slash_is_not_redirected(client, ndb_context):
    response = client.post("/123/api/udict/",
                           data={"json": '[{"word": "hat", "status": "ok"}]'},
                           follow_redirects=False)
    assert response.status_code == 200
    assert response.text == "1"


def test_udict_get_returns_words_newer_than_version(client, ndb_context):
    device, _ = _device("123")
    for word in ["hat", "cat", "rat"]:
        UserDictionaryWord(word=word, version=57, owner=device).put()
    for word in ["son", "run"]:
        UserDictionaryWord(word=word, version=56, owner=device).put()

    response = client.get("/123/api/udict/since/56")
    assert response.status_code == 200
    body = json.loads(response.text)
    assert body["version"] == 57
    assert len(body["words"]) == 3
    assert {w["word"] for w in body["words"]} == {"hat", "cat", "rat"}
    # `owner` is excluded; every other model field is present.
    assert set(body["words"][0]) == {"word", "status", "dictionary", "used",
                                     "added", "version"}


def test_udict_get_bare_route_returns_everything(client, ndb_context):
    device, _ = _device("123")
    UserDictionaryWord(word="hat", version=3, owner=device).put()
    body = json.loads(client.get("/123/api/udict").text)
    assert body == {"version": 3,
                    "words": [{"word": "hat", "status": "", "dictionary": 0,
                               "used": 0, "added": 0, "version": 3}]}


def test_udict_fans_out_over_linked_devices(client, ndb_context):
    devices = [Device(device_id="d{}".format(i)).put() for i in range(4)]
    User(devices=[devices[1], devices[2]]).put()
    User(devices=[devices[3]]).put()

    for i in range(4):
        client.post("/d{}/api/udict".format(i),
                    data={"json": '[{"word": "w%s", "status": "ok"}]' % i})

    expected_counts = [1, 2, 2, 1]
    for i, expected in enumerate(expected_counts):
        body = json.loads(client.get("/d{}/api/udict".format(i)).text)
        assert len(body["words"]) == expected, "device d{}".format(i)


def test_udict_word_validator_normalises(client, ndb_context):
    client.post("/123/api/udict", data={"json": '[{"word": "  HaT ", "status": "ok"}]'})
    assert [w.word for w in _all_udict_words()] == ["hat"]


# --------------------------------------------------------------------------
# Dropped routes
# --------------------------------------------------------------------------


@pytest.mark.parametrize("method,path", [
    ("get", "/dev1/pregame/get_current_game"),
    ("post", "/dev1/pregame/create"),
    ("get", "/api/settings/user/get/all"),
    ("post", "/save_game"),
    ("get", "/dev1/streams"),
    ("post", "/dev1/complain"),
    ("get", "/admin/global_dictionary/add_words"),
    ("get", "/news/list"),
    ("get", "/admin_panel/"),
    ("put", "/dev1/game_results/g1"),
    ("get", "/dev1/get_results/g1"),
    ("get", "/images/d_plot"),
    ("get", "/cron/notifications/update"),
])
def test_dropped_routes_404(client, ndb_context, method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 404, "{} {}".format(method, path)


def _all_udict_words():
    """Every UserDictionaryWord, bypassing OwnedModel.query's required owner."""
    return ndb.Query(kind="UserDictionaryWord").fetch()


def _device(device_id):
    from app.models import get_device_and_user

    return get_device_and_user(device_id)
