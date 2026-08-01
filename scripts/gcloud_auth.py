# -*- coding: utf-8 -*-
"""Credentials for the maintenance scripts.

Prefers Application Default Credentials. If they are not set up, falls back to
the token the gcloud CLI already holds, so that ``gcloud auth
application-default login`` is not a prerequisite for read-only work.
"""

import logging
import subprocess

logger = logging.getLogger(__name__)


def credentials():
    """Return credentials, or ``None`` to let the client library decide."""
    import google.auth
    from google.auth.exceptions import DefaultCredentialsError

    try:
        creds, _ = google.auth.default()
        return creds
    except DefaultCredentialsError:
        pass

    from google.oauth2.credentials import Credentials

    logger.info("no ADC found, using the gcloud CLI access token")
    token = subprocess.check_output(
        ["gcloud", "auth", "print-access-token"], text=True).strip()
    return Credentials(token=token)


def ndb_client(project):
    from google.cloud import ndb

    return ndb.Client(project=project, credentials=credentials())
