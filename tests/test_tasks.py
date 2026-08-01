# -*- coding: utf-8 -*-
"""The Cloud Tasks payload must be what the old push queue produced."""

import datetime
from urllib.parse import parse_qs

import pytest

from app import settings, tasks


class RecordingClient:
    def __init__(self):
        self.created = []

    def create_task(self, parent, task):
        self.created.append((parent, task))

        class Response:
            name = "projects/p/locations/l/queues/q/tasks/1"

        return Response()


@pytest.fixture
def recording(monkeypatch):
    client = RecordingClient()
    monkeypatch.setattr(tasks, "_tasks_client", lambda: client)
    monkeypatch.setattr(settings, "TASKS_DISABLED", False)
    return client


def test_task_targets_the_legacy_internal_url_with_a_form_body(recording, monkeypatch):
    monkeypatch.delenv("GAE_VERSION", raising=False)
    tasks.enqueue_stats_task("URLSAFE-KEY")

    parent, task = recording.created[0]
    assert parent.endswith("/queues/logs-processing")
    assert "/locations/us-central1" in parent

    request = task["app_engine_http_request"]
    assert request["relative_uri"] == "/internal/add_game_to_statistic"
    assert request["headers"]["Content-Type"] == "application/x-www-form-urlencoded"
    assert parse_qs(request["body"].decode()) == {"game_key": ["URLSAFE-KEY"]}
    assert "app_engine_routing" not in request


def test_task_is_delayed_by_five_seconds(recording):
    before = datetime.datetime.now(datetime.timezone.utc)
    tasks.enqueue_stats_task("k")
    _, task = recording.created[0]

    delay = (task["schedule_time"] - before).total_seconds()
    assert 4.0 <= delay <= 6.0


def test_task_is_pinned_to_the_enqueueing_version(recording, monkeypatch):
    """During the traffic split a py3 task must not land on the py27 version."""
    monkeypatch.setenv("GAE_VERSION", "py3")
    tasks.enqueue_stats_task("k")

    _, task = recording.created[0]
    assert task["app_engine_http_request"]["app_engine_routing"] == {
        "service": "default", "version": "py3"}


def test_disabled_tasks_are_not_enqueued(monkeypatch):
    client = RecordingClient()
    monkeypatch.setattr(tasks, "_tasks_client", lambda: client)
    monkeypatch.setattr(settings, "TASKS_DISABLED", True)

    assert tasks.enqueue_stats_task("k") is None
    assert client.created == []
