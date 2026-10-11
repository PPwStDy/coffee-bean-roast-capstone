"""Cloudlayer factory matching ITCS355 portability pattern."""
from __future__ import annotations

import os
from cloudlayer.base import StorageAdapter
from cloudlayer.local import LocalStorageAdapter


def get_cloud_adapter():
    from cloudlayer.config import settings
    if settings().get("CLOUD_PROVIDER") != "azure":
        raise ValueError("Full cloud capabilities require CLOUD_PROVIDER=azure")
    from cloudlayer.adapter import AzureCloudAdapter
    return AzureCloudAdapter()


def get_storage_adapter() -> StorageAdapter:
    provider = os.environ.get("CLOUD_PROVIDER", "local").lower()
    if provider == "local":
        return LocalStorageAdapter()
    elif provider == "gcp":
        from cloudlayer.gcp import GCPStorageAdapter
        return GCPStorageAdapter()
    elif provider == "azure":
        from cloudlayer.azure import AzureStorageAdapter
        return AzureStorageAdapter()
    raise ValueError(f"Unsupported CLOUD_PROVIDER: {provider}")
