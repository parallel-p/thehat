"""Cloud Tasks enqueueing.

Replaces the legacy ``taskqueue.add(url=..., params=..., countdown=5)`` push
queue. The task body is form-encoded so the target handler reads it exactly the
way ``AddGameHandler`` used to read ``self.request.get('game_key')``.
"""

import datetime
import logging
import os
from urllib.parse import urlencode

from app import settings

logger = logging.getLogger(__name__)

STATS_TASK_URL = "/internal/add_game_to_statistic"

_client = None


def _tasks_client():
    global _client
    if _client is None:
        from google.cloud import tasks_v2

        _client = tasks_v2.CloudTasksClient()
    return _client


def queue_path():
    from google.cloud import tasks_v2

    return tasks_v2.CloudTasksClient.queue_path(
        settings.PROJECT_ID, settings.TASKS_LOCATION, settings.TASKS_QUEUE
    )


def _routing():
    """Pin the task to the version that created it.

    During the WP8 traffic split the old python27 version still serves most
    default traffic. Without explicit routing a task enqueued by the py3
    version would be delivered to whichever version happens to answer, which
    is not what we want: the two versions encode urlsafe keys differently and
    only the enqueueing version is known to handle its own payload.
    """
    version = os.environ.get("GAE_VERSION")
    if not version:
        return None
    return {"service": settings.APPENGINE_SERVICE, "version": version}


def enqueue_stats_task(game_key_urlsafe, countdown=None):
    """Schedule the statistics pipeline for one game log.

    ``game_key_urlsafe`` is the urlsafe form of the ``GameLog`` key, as in the
    python27 app.
    """
    if settings.TASKS_DISABLED:
        logger.info("tasks disabled, not enqueueing %s", game_key_urlsafe)
        return None

    from google.cloud import tasks_v2

    if countdown is None:
        countdown = settings.STATS_TASK_COUNTDOWN

    request = {
        "http_method": tasks_v2.HttpMethod.POST,
        "relative_uri": STATS_TASK_URL,
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "body": urlencode({"game_key": game_key_urlsafe}).encode("utf-8"),
    }
    routing = _routing()
    if routing:
        request["app_engine_routing"] = routing

    task = {"app_engine_http_request": request}
    if countdown:
        task["schedule_time"] = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(seconds=countdown)

    response = _tasks_client().create_task(parent=queue_path(), task=task)
    logger.info("enqueued stats task %s for %s", response.name, game_key_urlsafe)
    return response.name
