"""Firebase Admin SDK initialization shared by Firestore and Storage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import firebase_admin
from firebase_admin import firestore, storage

from invoicex_backend.config import BackendSettings
from invoicex_backend.errors import IntegrationError


@dataclass(frozen=True)
class FirebaseResources:
    """Initialized Firebase clients used by the backend adapters."""

    app: firebase_admin.App
    firestore_client: Any
    storage_bucket: Any


def create_firebase_resources(settings: BackendSettings) -> FirebaseResources:
    """Initialize a named Firebase app with Application Default Credentials."""

    options = {
        "projectId": settings.firebase_project_id,
        "storageBucket": settings.resolved_firebase_storage_bucket(),
    }
    try:
        try:
            app = firebase_admin.get_app(settings.firebase_app_name)
        except ValueError:
            app = firebase_admin.initialize_app(
                options=options,
                name=settings.firebase_app_name,
            )
        firestore_client = firestore.client(
            app=app,
            database_id=settings.firebase_firestore_database,
        )
        storage_bucket = storage.bucket(app=app)
    except Exception as exc:
        raise IntegrationError(
            "Firebase initialization failed. Check the project ID, bucket, "
            "and Application Default Credentials."
        ) from exc

    return FirebaseResources(
        app=app,
        firestore_client=firestore_client,
        storage_bucket=storage_bucket,
    )
