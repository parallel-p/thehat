"""Runtime configuration.

Everything is derived from the environment so that the same image runs against
``the-hat`` (production) and ``the-hat-staging`` without code changes.
"""

import os


def _project() -> str:
    for var in ("GOOGLE_CLOUD_PROJECT", "GCLOUD_PROJECT", "DATASTORE_PROJECT_ID"):
        value = os.environ.get(var)
        if value:
            return value
    return "the-hat"


PROJECT_ID = _project()

# App Engine's default GCS bucket. Dictionary blobs live under /dictionary/<key>.
GCS_BUCKET = os.environ.get("DICTIONARY_BUCKET", "{}.appspot.com".format(PROJECT_ID))

# Cloud Tasks queue replacing the legacy `logs-processing` push queue.
TASKS_LOCATION = os.environ.get("TASKS_LOCATION", "us-central1")
TASKS_QUEUE = os.environ.get("TASKS_QUEUE", "logs-processing")

# Delay before the statistics task fires, seconds. Matches the old
# `taskqueue.add(..., countdown=5)`.
STATS_TASK_COUNTDOWN = int(os.environ.get("STATS_TASK_COUNTDOWN", "5"))

# App Engine service the Cloud Tasks App Engine target should hit. Empty means
# "the version that is currently serving default traffic", which is what we
# want both before and after the cutover.
APPENGINE_SERVICE = os.environ.get("GAE_SERVICE", "default")

# True while running on App Engine (as opposed to local tests / scripts).
ON_APPENGINE = bool(os.environ.get("GAE_ENV"))

# Set by tests and by scripts that must never enqueue anything.
TASKS_DISABLED = os.environ.get("TASKS_DISABLED", "").lower() in ("1", "true", "yes")
