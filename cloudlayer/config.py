"""Layer 2 configuration. Never print credentials or silently invent cloud resources."""

import os
from pathlib import Path
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
SLOTS = {
    "provider": ("CLOUD_PROVIDER",),
    "project": ("PROJECT_ID",),
    "region": ("REGION",),
    "storage": ("BLOB_URI",),
    "registry": ("CONTAINER_REGISTRY",),
    "tracking": ("MLFLOW_TRACKING_URI",),
    "model registry": ("MODEL_REGISTRY_NAME",),
    "identity": ("IDENTITY_REF",),
}


def settings():
    return {**dotenv_values(ROOT / "cloud.env"), **os.environ}


def check():
    config = settings()
    passed = True
    for slot, keys in SLOTS.items():
        valid = all(config.get(key, "").strip() for key in keys)
        print(f"{'PASS' if valid else 'FAIL'} {slot}: {', '.join(keys)}")
        passed &= valid
    if config.get("CLOUD_PROVIDER") not in {"azure", "local"}:
        print("FAIL provider: this capstone implements Azure and local storage")
        passed = False
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(check())
