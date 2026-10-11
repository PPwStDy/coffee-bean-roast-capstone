"""Roast dataset contracts and Iteration4's color-preserving preprocessing."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import torch
from PIL import Image
from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder
import torchvision.transforms.v2 as T
from src.config import CLASSES, DATA_DIR, IMAGE_SIZE, IMAGENET_MEAN, IMAGENET_STD

SOURCE_DATASET_PATH = Path(os.environ.get("SOURCE_DATASET_PATH", DATA_DIR))


def pixel_hash(path: Path) -> str:
    with Image.open(path) as image:
        image = image.convert("RGB")
        digest = hashlib.sha256(f"{image.width}x{image.height}:".encode())
        digest.update(image.tobytes())
    return digest.hexdigest()


def get_train_transforms():
    return T.Compose(
        [
            T.RandomResizedCrop(IMAGE_SIZE, scale=(0.85, 1.0), antialias=True),
            T.RandomHorizontalFlip(0.5),
            T.RandomVerticalFlip(0.5),
            T.RandomRotation(180),
            T.ToImage(),
            T.ToDtype(torch.float32, scale=True),
            T.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
    )


def get_eval_transforms():
    return T.Compose(
        [
            T.Resize((IMAGE_SIZE, IMAGE_SIZE), antialias=True),
            T.ToImage(),
            T.ToDtype(torch.float32, scale=True),
            T.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
    )


def validate_dataset(data_dir: Path = DATA_DIR) -> dict[str, int]:
    """Reject missing classes, unreadable images, and duplicate pixels in any split."""
    seen = {}
    counts = {}
    manifest_path = Path(data_dir) / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    records = {}
    if manifest:
        if manifest["classes"] != CLASSES or manifest["prepared_counts"] != {
            "train": 835,
            "valid": 178,
            "test": 181,
        }:
            raise ValueError("Manifest class order or frozen split counts changed")
        for record in manifest["source_records"]:
            records.setdefault(record["prepared_path"], []).append(record)
    for split in ("train", "valid", "test"):
        dataset = ImageFolder(Path(data_dir) / split)
        if dataset.classes != CLASSES:
            raise ValueError(f"Class order mismatch in {split}: {dataset.classes}; expected {CLASSES}")
        counts[split] = len(dataset)
        for filename, _ in dataset.samples:
            path = Path(filename)
            with Image.open(path) as image:
                image.load()
                if image.mode != "RGB" or image.size != (IMAGE_SIZE, IMAGE_SIZE):
                    raise ValueError(f"Expected RGB {IMAGE_SIZE}x{IMAGE_SIZE}: {path}")
            digest = pixel_hash(path)
            if manifest:
                relative = path.relative_to(data_dir).as_posix()
                matching = records.get(relative, [])
                file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
                if not matching or any(r["pixel_sha256"] != digest for r in matching):
                    raise ValueError(f"Manifest pixel hash mismatch: {path}")
                if file_hash not in {r["file_sha256"] for r in matching} or path.stem != digest:
                    raise ValueError(f"Manifest content hash mismatch: {path}")
            if digest in seen:
                raise ValueError(f"Duplicate image content: {seen[digest]} and {path}")
            seen[digest] = path
    if manifest and (counts != manifest["prepared_counts"] or len(records) != sum(counts.values())):
        raise ValueError("Manifest contents and prepared dataset differ")
    return counts


def setup_data_directory(dest_dir: Path = DATA_DIR) -> None:
    if SOURCE_DATASET_PATH.resolve() != Path(dest_dir).resolve():
        from src.prepare_roast_data import prepare_dataset

        prepare_dataset(SOURCE_DATASET_PATH, Path(dest_dir))
    validate_dataset(Path(dest_dir))


def get_dataloaders(data_dir: Path = DATA_DIR, batch_size=32, num_workers=0):
    validate_dataset(data_dir)
    datasets = [
        ImageFolder(
            Path(data_dir) / split,
            transform=(get_train_transforms() if split == "train" else get_eval_transforms()),
        )
        for split in ("train", "valid", "test")
    ]
    return tuple(
        DataLoader(dataset, batch_size=batch_size, shuffle=(i == 0), num_workers=num_workers)
        for i, dataset in enumerate(datasets)
    )
