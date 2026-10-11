"""Azure Blob Storage adapter."""

from __future__ import annotations

import os
from pathlib import Path
from cloudlayer.base import StorageAdapter


class AzureStorageAdapter(StorageAdapter):
    def download_file(self, remote_uri: str, local_path: Path) -> Path:
        from azure.storage.blob import BlobServiceClient

        # URI format: abfss://container-name/path/to/blob or https://...
        parts = remote_uri.replace("abfss://", "").split("/", 1)
        container_name, blob_name = parts[0], parts[1]

        service_client = BlobServiceClient.from_connection_string(
            os.environ["AZURE_STORAGE_CONNECTION_STRING"]
        )
        blob_client = service_client.get_blob_client(container=container_name, blob=blob_name)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(blob_client.download_blob().readall())
        return local_path

    def upload_file(self, local_path: Path, remote_uri: str) -> None:
        from azure.storage.blob import BlobServiceClient

        parts = remote_uri.replace("abfss://", "").split("/", 1)
        container_name, blob_name = parts[0], parts[1]

        service_client = BlobServiceClient.from_connection_string(
            os.environ["AZURE_STORAGE_CONNECTION_STRING"]
        )
        blob_client = service_client.get_blob_client(container=container_name, blob=blob_name)
        with open(local_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
