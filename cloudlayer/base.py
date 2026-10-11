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


class CloudAdapter(ABC):
    """The eleven operations required by the ITCS355 portability contract."""

    @abstractmethod
    def upload(self, local_path: str, key: str) -> str: ...

    @abstractmethod
    def download(self, uri: str, local_path: str) -> None: ...

    @abstractmethod
    def push_image(self, local_tag: str) -> str: ...

    @abstractmethod
    def submit_training(self, image_uri: str, args: dict) -> str: ...

    @abstractmethod
    def wait_training(self, job_id: str) -> dict: ...

    @abstractmethod
    def register_model(self, model_uri: str, name: str) -> str: ...

    @abstractmethod
    def deploy(self, model_ref: str, endpoint: str, instance: str) -> str: ...

    @abstractmethod
    def invoke(self, endpoint: str, payload: dict) -> dict: ...

    @abstractmethod
    def emit_metric(self, name: str, value: float, unit: str) -> None: ...

    def generate(self, prompt: str, params: dict) -> dict:
        raise NotImplementedError("Optional generation capability is unused by roast classification")

    @abstractmethod
    def teardown(self, tags: dict) -> list[str]: ...
