"""Local filesystem storage adapter implementation."""
from __future__ import annotations

import shutil
from pathlib import Path

from cloudlayer.base import StorageAdapter


class LocalStorageAdapter(StorageAdapter):
    def download_file(self, remote_uri: str, local_path: Path) -> Path:
        src = Path(remote_uri.replace("file://", ""))
        local_path.parent.mkdir(parents=True, exist_ok=True)
        if src != local_path:
            shutil.copy2(src, local_path)
        return local_path

    def upload_file(self, local_path: Path, remote_uri: str) -> None:
        dest = Path(remote_uri.replace("file://", ""))
        dest.parent.mkdir(parents=True, exist_ok=True)
        if local_path != dest:
            shutil.copy2(local_path, dest)
