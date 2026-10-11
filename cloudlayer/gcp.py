"""GCP Cloud Storage adapter."""

from __future__ import annotations

from pathlib import Path
from cloudlayer.base import StorageAdapter


class GCPStorageAdapter(StorageAdapter):
    def download_file(self, remote_uri: str, local_path: Path) -> Path:
        from google.cloud import storage

        # URI format: gs://bucket-name/path/to/blob
        parts = remote_uri.replace("gs://", "").split("/", 1)
        bucket_name, blob_name = parts[0], parts[1]

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(local_path))
        return local_path

    def upload_file(self, local_path: Path, remote_uri: str) -> None:
        from google.cloud import storage

        parts = remote_uri.replace("gs://", "").split("/", 1)
        bucket_name, blob_name = parts[0], parts[1]

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(str(local_path))
