"""Configuration for coffee bean roast classification using Iteration4 Swin-T."""

from __future__ import annotations

import os
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT_DIR / "data" / "coffee_bean_roast"))
REPORTS_DIR = Path(os.environ.get("REPORTS_DIR", ROOT_DIR / "reports"))
MODELS_DIR = ROOT_DIR / "reports"
MODEL_PATH = Path(os.environ.get("MODEL_PATH", REPORTS_DIR / "model.onnx"))
TORCHSCRIPT_MODEL_PATH = Path(os.environ.get("TORCHSCRIPT_MODEL_PATH", REPORTS_DIR / "model.pt"))

# Model & Preprocessing Specifications
CLASSES = ["Dark", "Green", "Light", "Medium"]
NUM_CLASSES = len(CLASSES)
IDX_TO_CLASS = {idx: name for idx, name in enumerate(CLASSES)}

# This order matches ImageFolder and the Iteration4 checkpoint.
CLASS_LABEL_ALIASES = {name.casefold(): name for name in CLASSES}


def canonical_class_name(label: str) -> str | None:
    """Map a dataset label to the stable API class name."""
    return CLASS_LABEL_ALIASES.get(label.strip().casefold())


CLASS_TO_IDX = {name: idx for idx, name in enumerate(CLASSES)}

IMAGE_SIZE = 224  # Standard input resolution (224x224)
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

# Deliberate Failure Mode: Optical Glare & Occlusion Guard Thresholds
# Standard deviation of pixel values in normalized [0, 1] range.
# A natural bean image with background typically has std dev > 0.12.
# Specular glare (pure white) or optical lens occlusion (pure black/gray) collapses std dev < 0.05.
MIN_PIXEL_STD_THRESHOLD = float(os.environ.get("MIN_PIXEL_STD_THRESHOLD", "0.05"))
MIN_SHANNON_ENTROPY_THRESHOLD = float(os.environ.get("MIN_SHANNON_ENTROPY_THRESHOLD", "1.0"))

# Service & SLO Targets
LATENCY_BUDGET_MS = 120.0  # p95 SLO target: 120ms
MODEL_VERSION = os.environ.get("MODEL_VERSION", "roast-iteration4-swin-v1")
ARCHITECTURE = "PretrainedSwinT"
MODEL_METADATA_PATH = Path(os.environ.get("MODEL_METADATA_PATH", REPORTS_DIR / "model_metadata.json"))
IMPORTED_CHECKPOINT_PATH = ROOT_DIR / "models" / "iteration4_swin.pth"
MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", f"sqlite:///{ROOT_DIR}/mlflow.db")
MLFLOW_EXPERIMENT_NAME = "coffee-bean-roast-classification"
MLFLOW_REGISTERED_MODEL_NAME = "coffee-bean-roast-classifier"
