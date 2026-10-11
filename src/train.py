"""Automated, reproducible training pipeline with MLflow tracking and lineage."""
from __future__ import annotations

import hashlib
import json
import os
import re
import random
import argparse
import subprocess
import importlib.metadata
import time

import mlflow
import numpy as np
import torch
import torch.nn as nn
import torchvision
from sklearn.metrics import f1_score
from torch.optim import AdamW
from torch.optim.lr_scheduler import OneCycleLR

from src.config import (
    ARCHITECTURE,
    CLASSES,
    DATA_DIR,
    MLFLOW_EXPERIMENT_NAME,
    MLFLOW_TRACKING_URI,
    NUM_CLASSES,
    REPORTS_DIR,
    ROOT_DIR,
)
from src.data import get_dataloaders, setup_data_directory
from src.model import build_model


def set_seed(seed: int = 42) -> None:
    """Enforces strict deterministic training."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def get_dataset_revision() -> str:
    """Return the DVC directory hash used for this training run."""
    pointer = DATA_DIR.with_suffix(".dvc")
    if not pointer.exists():
        raise FileNotFoundError(f"Missing DVC dataset pointer: {pointer}")
    match = re.search(r"^\s*-\s+md5:\s*(\S+)", pointer.read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        raise ValueError(f"Could not read dataset revision from {pointer}")
    return match.group(1)


def train_epoch(model: nn.Module, loader, criterion, optimizer, device, scheduler) -> tuple[float, float]:
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    for step, (images, labels) in enumerate(loader, 1):
        images, labels = images.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        scheduler.step()
        if step % 10 == 0:
            print(f"  batch {step}/{len(loader)} loss={loss.item():.4f}", flush=True)

        running_loss += loss.item() * images.size(0)
        _, preds = torch.max(outputs, 1)
        correct += (preds == labels).sum().item()
        total += labels.size(0)

    return running_loss / total, correct / total


def evaluate(model: nn.Module, loader, criterion, device) -> tuple[float, float, float, np.ndarray, np.ndarray]:
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            loss = criterion(outputs, labels)

            running_loss += loss.item() * images.size(0)
            _, preds = torch.max(outputs, 1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    macro_f1 = f1_score(all_labels, all_preds, average="macro", zero_division=0)
    return running_loss / total, correct / total, float(macro_f1), np.array(all_preds), np.array(all_labels)


def train(
    epochs: int = 20,
    batch_size: int = 32,
    lr: float = 5e-5,
    seed: int = 42,
) -> dict:
    code_revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT_DIR, text=True).strip()
    if subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT_DIR, text=True).strip():
        raise RuntimeError("Commit source changes before training so model lineage identifies actual code")
    started = time.perf_counter()
    set_seed(seed)
    torch.set_num_threads(2)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    setup_data_directory(DATA_DIR)
    dataset_revision = get_dataset_revision()

    train_loader, val_loader, test_loader = get_dataloaders(DATA_DIR, batch_size=batch_size)

    device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Training on device: {device}; batch size={batch_size}", flush=True)

    model = build_model(num_classes=NUM_CLASSES, pretrained=True).to(device)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
    optimizer = AdamW(model.get_param_groups(backbone_lr=lr, head_lr=1e-3))
    scheduler = OneCycleLR(optimizer, max_lr=[lr * 4, 1e-3 * 2.5],
                           steps_per_epoch=len(train_loader), epochs=epochs, pct_start=0.2)

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

    best_val_loss = float("inf")
    model_version = os.environ.get("MODEL_VERSION", "roast-swin-retrained-v1")
    best_weights_path = REPORTS_DIR / "model_best.pth"

    with mlflow.start_run(run_name=f"run_{model_version}"):
        mlflow.log_params({
            "model_version": model_version,
            "architecture": ARCHITECTURE,
            "epochs": epochs,
            "batch_size": batch_size,
            "backbone_learning_rate": lr,
            "head_learning_rate": 1e-3,
            "label_smoothing": 0.05,
            "scheduler": "OneCycleLR",
            "initialization": "ImageNet; imported checkpoint not used",
            "optimizer": "AdamW",
            "seed": seed,
            "num_classes": NUM_CLASSES,
            "classes": CLASSES,
            "dataset_dvc_hash": dataset_revision,
            "code_revision": code_revision,
            "torch_version": torch.__version__,
            "torchvision_version": torchvision.__version__,
            "numpy_version": np.__version__,
        })

        history = []
        best_epoch = 0
        for epoch in range(1, epochs + 1):
            train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer, device, scheduler)
            val_loss, val_acc, val_f1, _, _ = evaluate(model, val_loader, criterion, device)

            print(f"Epoch {epoch:02d}/{epochs:02d} - Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | Val Loss: {val_loss:.4f} Acc: {val_acc:.4f} Macro-F1: {val_f1:.4f}")

            mlflow.log_metrics({
                "train_loss": train_loss,
                "train_acc": train_acc,
                "val_loss": val_loss,
                "val_acc": val_acc,
                "val_f1": val_f1,
            }, step=epoch)

            history.append({"epoch": epoch, "train_loss": train_loss, "train_accuracy": train_acc,
                            "validation_loss": val_loss, "validation_accuracy": val_acc, "validation_macro_f1": val_f1})
            (REPORTS_DIR / "training_history.json").write_text(json.dumps(history, indent=2) + "\n")
            if val_loss < best_val_loss:
                best_epoch = epoch
                best_val_loss = val_loss
                torch.save(model.state_dict(), best_weights_path)

        summary = {
            "model_version": model_version,
            "architecture": ARCHITECTURE,
            "dataset_dvc_hash": dataset_revision,
            "code_revision": code_revision,
            "checkpoint_sha256": hashlib.sha256(best_weights_path.read_bytes()).hexdigest(),
            "evaluation_status": "retrained_on_deduplicated_splits",
            "split_counts": {"train": len(train_loader.dataset), "valid": len(val_loader.dataset), "test": len(test_loader.dataset)},
            "test_evaluation": "reserved for selected export; not evaluated during training",
            "best_epoch": best_epoch,
            "best_validation_loss": best_val_loss,
            "seed": seed,
            "initialization": "torchvision Swin_T_Weights.IMAGENET1K_V1",
            "parameters": {"epochs": epochs, "batch_size": batch_size, "backbone_lr": lr,
                           "head_lr": 1e-3, "weight_decay": .01, "label_smoothing": .05,
                           "scheduler": "OneCycleLR", "pct_start": .2},
            "dependencies": {p: importlib.metadata.version(p) for p in ["torch", "torchvision", "numpy", "pillow", "mlflow", "onnx", "onnxruntime"]},
            "device": str(device),
            "training_duration_seconds": time.perf_counter() - started,
            "mlflow_run_id": mlflow.active_run().info.run_id,
            "dependency_lock_sha256": hashlib.sha256((ROOT_DIR / "uv.lock").read_bytes()).hexdigest(),
            "classes": CLASSES,
        }
        summary_path = REPORTS_DIR / "training_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        mlflow.log_artifact(str(best_weights_path), artifact_path="checkpoints")
        mlflow.log_artifact(str(summary_path), artifact_path="lineage")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    train(epochs=args.epochs, batch_size=args.batch_size, seed=args.seed)
