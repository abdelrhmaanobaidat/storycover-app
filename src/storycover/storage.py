from datetime import timedelta

import google.auth
import google.auth.transport.requests
from google.cloud import storage

from .config import settings

_client: storage.Client | None = None


def _bucket() -> storage.Bucket:
    global _client
    if _client is None:
        _client = storage.Client()
    if not settings.gcs_bucket:
        raise RuntimeError("GCS_BUCKET is not set")
    return _client.bucket(settings.gcs_bucket)


def upload_cover(name: str, data: bytes, content_type: str) -> str:
    """Store the cover and return a short-lived signed URL for the client."""
    blob = _bucket().blob(name)
    blob.upload_from_string(data, content_type=content_type)
    return _signed_url(blob, content_type)


def _signed_url(blob: storage.Blob, content_type: str) -> str:
    # On GKE with Workload Identity there is no private key, so sign through the IAM
    # SignBlob API using the runtime SA's access token (needs serviceAccountTokenCreator).
    creds, _ = google.auth.default()
    creds.refresh(google.auth.transport.requests.Request())
    email = settings.signer_service_account or getattr(creds, "service_account_email", None)
    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(seconds=settings.signed_url_ttl_seconds),
        method="GET",
        response_type=content_type,
        service_account_email=email,
        access_token=creds.token,
    )
