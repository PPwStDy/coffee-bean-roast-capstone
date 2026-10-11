"""Data contracts for the prepared coffee roast dataset."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from PIL import Image
from torchvision.datasets import ImageFolder
from src.config import CLASSES, DATA_DIR, IMAGE_SIZE
from src.data import pixel_hash


@pytest.fixture(scope="session")
def dataset_root() -> Path:
    if not (DATA_DIR / "manifest.json").exists():
        pytest.fail("Prepared roast dataset missing; run make dvc-pull or prepare the source")
    return DATA_DIR


def test_schema_columns_present_and_exact(dataset_root):
    for split in ("train", "valid", "test"):
        dataset = ImageFolder(dataset_root / split)
        assert dataset.classes == CLASSES
        assert dataset.class_to_idx == {name: i for i, name in enumerate(CLASSES)}


def test_no_null_or_empty_rows(dataset_root):
    manifest = json.loads((dataset_root / "manifest.json").read_text())
    assert manifest["classes"] == CLASSES
    for split in ("train", "valid", "test"):
        dataset = ImageFolder(dataset_root / split)
        assert len(dataset) == manifest["prepared_counts"][split]
        for name in CLASSES:
            assert len(list((dataset_root / split / name).glob("*.png"))) > 0


def test_labels_are_strictly_one_hot(dataset_root):
    # ImageFolder provides one integer class per image rather than the old one-hot CSV.
    for split in ("train", "valid", "test"):
        dataset = ImageFolder(dataset_root / split)
        for path, label in dataset.samples:
            assert label in range(len(CLASSES))
            assert Path(path).parent.name == CLASSES[label]


def test_all_referenced_images_exist_and_readable(dataset_root):
    for split in ("train", "valid", "test"):
        for path, _ in ImageFolder(dataset_root / split).samples:
            with Image.open(path) as image:
                image.load()
                assert image.mode == "RGB"
                assert image.size == (IMAGE_SIZE, IMAGE_SIZE)


def test_no_image_leaks_across_splits(dataset_root):
    seen = {}
    for split in ("train", "valid", "test"):
        for filename, _ in ImageFolder(dataset_root / split).samples:
            path = Path(filename)
            digest = pixel_hash(path)
            assert digest not in seen, f"Repeated pixels: {seen.get(digest)} and {path}"
            seen[digest] = path
