"""Base abstraction for cloud storage layer (Three-Layer Portability Contract)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class StorageAdapter(ABC):
    """Abstract interface isolating cloud provider SDKs from core code (Layer 1)."""

    @abstractmethod
    def download_file(self, remote_uri: str, local_path: Path) -> Path:
        """Downloads a remote object to a local filesystem destination."""
        pass

    @abstractmethod
    def upload_file(self, local_path: Path, remote_uri: str) -> None:
        """Uploads a local file to remote object storage."""
        pass
