# -*- coding: utf-8 -*-
"""Credential resolution for the Google Cloud client libraries.

On App Engine there is nothing to do -- the runtime provides the service
account. Off App Engine (the maintenance jobs in ``scripts/`` and
``python -m app.dictionary_gen``) Application Default Credentials are used if
present, and otherwise the token the gcloud CLI already holds, so that
``gcloud auth application-default login`` is not a hard prerequisite.
"""

import logging
import subprocess

from app import settings

logger = logging.getLogger(__name__)


def credentials():
    """Return credentials, or ``None`` to let the client library decide."""
    if settings.ON_APPENGINE:
        return None

    import google.auth
    from google.auth.exceptions import DefaultCredentialsError

    try:
        creds, _ = google.auth.default()
        return creds
    except DefaultCredentialsError:
        pass

    from google.oauth2.credentials import Credentials

    logger.info("no application default credentials; using the gcloud CLI token")
    try:
        token = subprocess.check_output(
            ["gcloud", "auth", "print-access-token"], text=True).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise RuntimeError(
            "no credentials available: set up Application Default Credentials "
            "with `gcloud auth application-default login`") from error
    return Credentials(token=token)
