# -*- coding: utf-8 -*-
"""Credentials for the maintenance scripts.

Thin wrapper over :mod:`app.gcp_auth` so the scripts and the application resolve
credentials the same way.
"""

from app.gcp_auth import credentials  # noqa: F401  (re-exported)


def ndb_client(project):
    from google.cloud import ndb

    return ndb.Client(project=project, credentials=credentials())
