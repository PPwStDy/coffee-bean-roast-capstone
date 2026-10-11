"""Audit the source and create deterministic, deduplicated 70/15/15 splits."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import shutil
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from PIL import Image
from src.config import CLASSES, DATA_DIR, IMAGE_SIZE, REPORTS_DIR
from src.data import pixel_hash, validate_dataset


def prepare_dataset(source: Path, destination: Path = DATA_DIR, seed=42) -> dict:
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination or source in destination.parents or destination in source.parents:
        raise ValueError("Source and destination must be separate directories")
    if destination.exists():
        raise FileExistsError(f"Prepared data exists: {destination}; use dvc pull or a new destination")
    records = []
    groups = defaultdict(list)
    for split in ("train", "test"):
        split_dir = source / split
        if not split_dir.is_dir() or sorted(p.name for p in split_dir.iterdir() if p.is_dir()) != CLASSES:
            raise ValueError(f"Expected classes {CLASSES} in {split_dir}")
        for label in CLASSES:
            paths = sorted((split_dir / label).glob("*.png"))
            if not paths:
                raise ValueError(f"Empty class: {split_dir / label}")
            for path in paths:
                with Image.open(path) as image:
                    image.load()
                    if image.mode != "RGB" or image.size != (IMAGE_SIZE, IMAGE_SIZE):
                        raise ValueError(f"Expected RGB {IMAGE_SIZE}x{IMAGE_SIZE}: {path}")
                record = {"source_path": path.relative_to(source).as_posix(), "label": label,
                          "original_split": split, "pixel_sha256": pixel_hash(path),
                          "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                records.append(record)
                groups[record["pixel_sha256"]].append(record)
    csv_path = source / "Coffee Bean.csv"
    with csv_path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["class index", "filepaths", "labels", "data set"]:
            raise ValueError(f"Unexpected CSV columns: {reader.fieldnames}")
        rows = list(reader)
    bypath = {r["source_path"]: r for r in records}
    if len(rows) != len(records) or {r["filepaths"] for r in rows} != set(bypath):
        raise ValueError("Source CSV and image inventory do not match")
    for row in rows:
        record = bypath[row["filepaths"]]
        if (row["labels"] != record["label"] or row["data set"] != record["original_split"]
                or int(row["class index"]) != CLASSES.index(record["label"])):
            raise ValueError(f"Incorrect CSV label/index: {row}")
    for group in groups.values():
        if len({r["label"] for r in group}) != 1:
            raise ValueError(f"Conflicting labels for identical pixels: {group}")
    train_hashes = {r["pixel_sha256"] for r in records if r["original_split"] == "train"}
    leaked = [r for r in records if r["original_split"] == "test" and r["pixel_sha256"] in train_hashes]
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".roast-prepare-", dir=destination.parent))
    try:
        rng = random.Random(seed)
        for label in CLASSES:
            hashes = sorted(h for h, group in groups.items() if group[0]["label"] == label)
            rng.shuffle(hashes)
            train_end = int(len(hashes) * 0.70)
            valid_end = train_end + int(len(hashes) * 0.15)
            for split, members in (("train", hashes[:train_end]), ("valid", hashes[train_end:valid_end]),
                                   ("test", hashes[valid_end:])):
                folder = staging / split / label
                folder.mkdir(parents=True)
                for digest in members:
                    relative = Path(split) / label / f"{digest}.png"
                    shutil.copy2(source / groups[digest][0]["source_path"], staging / relative)
                    for record in groups[digest]:
                        record["prepared_path"] = relative.as_posix()
        counts = validate_dataset(staging)
        report = {"classes": CLASSES, "seed": seed, "split_fractions": [0.70, 0.15, 0.15],
                  "source_image_count": len(records), "unique_image_count": len(groups),
                  "duplicate_copies_removed": len(records) - len(groups),
                  "original_test_count": sum(r["original_split"] == "test" for r in records),
                  "original_test_images_also_in_train": len(leaked),
                  "original_test_overlap_by_class": dict(Counter(r["label"] for r in leaked)),
                  "prepared_counts": counts,
                  "prepared_class_counts": {s: {c: len(list((staging / s / c).glob('*.png'))) for c in CLASSES}
                                            for s in counts},
                  "license": "CC BY-SA 4.0",
                  "dataset_sources": ["https://www.kaggle.com/datasets/gpiosenka/coffee-bean-dataset-resized-224-x-224",
                                      "https://www.kaggle.com/datasets/sot2542/coffee-bean-dataset-v1"],
                  "dataset_source_versions": [1, 1],
                  "research_citation": "Ontoum et al. (2022), Coffee Roast Intelligence, arXiv:2206.01841",
                  "modifications": "Exact-pixel deduplication, hash filenames, stratified 70/15/15 resplitting with seed 42",
                  "evaluation_warning": "The imported checkpoint saw the original training images. "
                    "A new split does not make its evaluation independent. Retrain from ImageNet weights "
                    "on the prepared training split or collect unseen evaluation images.",
                  "source_records": records}
        (staging / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
        staging.rename(destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "dataset_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "source_records"}, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--destination", type=Path, default=DATA_DIR)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    prepare_dataset(args.source, args.destination, args.seed)
