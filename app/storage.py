"""Google Cloud Storage access for the generated dictionary blobs.

Replaces the App Engine ``lib/cloudstorage`` shim. Object layout is unchanged:
``gs://<default bucket>/dictionary/<gcs_key>``.
"""

import logging
import threading

from app import settings
from app.gcp_auth import credentials

logger = logging.getLogger(__name__)

_client = None
_lock = threading.Lock()

# The dictionary blob is ~1.3 MB and changes only when the generation job runs,
# so one in-process copy per instance saves a GCS round trip per request.
_cache = {}


def _storage_client():
    global _client
    if _client is None:
        from google.cloud import storage

        _client = storage.Client(project=settings.PROJECT_ID,
                                 credentials=credentials())
    return _client


def dictionary_blob_name(key):
    return "dictionary/{}".format(key)


def read_dictionary_blob(key):
    cached = _cache.get(key)
    if cached is not None:
        return cached
    bucket = _storage_client().bucket(settings.GCS_BUCKET)
    data = bucket.blob(dictionary_blob_name(key)).download_as_bytes()
    with _lock:
        _cache.clear()
        _cache[key] = data
    return data


def write_dictionary_blob(key, data, content_type="application/json"):
    bucket = _storage_client().bucket(settings.GCS_BUCKET)
    bucket.blob(dictionary_blob_name(key)).upload_from_string(
        data, content_type=content_type
    )


def delete_dictionary_blob(key):
    bucket = _storage_client().bucket(settings.GCS_BUCKET)
    blob = bucket.blob(dictionary_blob_name(key))
    if blob.exists():
        blob.delete()
