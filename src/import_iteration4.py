"""Import the user's Swin checkpoint and record its provenance without claiming a clean evaluation."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
import torch
from src.config import (ARCHITECTURE, CLASSES, DATA_DIR, IMPORTED_CHECKPOINT_PATH,
                        MLFLOW_EXPERIMENT_NAME, MLFLOW_REGISTERED_MODEL_NAME,
                        MLFLOW_TRACKING_URI, MODEL_VERSION, REPORTS_DIR, ROOT_DIR)
from src.model import build_model


def import_checkpoint(source_dir: Path):
    source_dir = Path(source_dir)
    checkpoint = source_dir / "model_best_vloss_swin.pth"
    torch.set_num_threads(1)
    model = build_model(pretrained=False)
    model.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True), strict=True)
    model.eval()
    IMPORTED_CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(checkpoint, IMPORTED_CHECKPOINT_PATH)
    provenance = ROOT_DIR / "provenance" / "iteration4"
    provenance.mkdir(parents=True, exist_ok=True)
    for name in ("model.py", "dataset.py", "trainer.py", "dl_utils.py", "test_summary_swin.txt"):
        shutil.copy2(source_dir / name, provenance / name)
    audit = json.loads((DATA_DIR / "manifest.json").read_text())
    summary = {
        "architecture": ARCHITECTURE, "classes": CLASSES, "model_version": MODEL_VERSION,
        "checkpoint_sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        "checkpoint_file": "models/iteration4_swin.pth",
        "original_source": "DL_FinalProject/Iteration4/model_best_vloss_swin.pth",
        "original_reported_accuracy": 0.9975,
        "original_reported_macro_f1": 0.9975,
        "original_test_images_also_in_train": audit["original_test_images_also_in_train"],
        "evaluation_status": "contaminated_original_split",
        "evaluation_warning": audit["evaluation_warning"],
        "training_dataset_lineage": "Original source file inventory is in the prepared dataset manifest; "
            "this checkpoint was NOT trained on the new clean split.",
        "license": audit["license"],
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / "iteration4_import.json"
    path.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return summary


def register_checkpoint():
    import mlflow
    import mlflow.pytorch
    import numpy as np
    from mlflow.models import ModelSignature
    from mlflow.types.schema import Schema, TensorSpec
    from src.train import get_dataset_revision
    path = REPORTS_DIR / "iteration4_import.json"
    summary = json.loads(path.read_text())
    torch.set_num_threads(1)
    model = build_model(pretrained=False)
    model.load_state_dict(torch.load(IMPORTED_CHECKPOINT_PATH, map_location="cpu", weights_only=True))
    model.eval()
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)
    with mlflow.start_run(run_name=summary["model_version"]) as run:
        mlflow.log_params({key: summary[key] for key in (
            "architecture", "classes", "checkpoint_sha256", "evaluation_status")})
        mlflow.set_tag("evaluation_warning", summary["evaluation_warning"])
        mlflow.set_tag("origin", summary["original_source"])
        mlflow.log_param("prepared_dataset_dvc_hash", get_dataset_revision())
        mlflow.log_param("prepared_dataset_used_for_training", False)
        mlflow.log_artifact(str(IMPORTED_CHECKPOINT_PATH), artifact_path="checkpoints")
        mlflow.log_artifacts(str(ROOT_DIR / "provenance" / "iteration4"), artifact_path="original_source")
        logged = mlflow.pytorch.log_model(model, name="model",
                                         serialization_format="pickle",
                                         code_paths=[str(ROOT_DIR / "src")],
                                         pip_requirements=["torch==2.5.1", "torchvision==0.20.1", "numpy==1.26.4", "pillow>=10"],
                                         signature=ModelSignature(
                                             inputs=Schema([TensorSpec(np.dtype("float32"), (-1, 3, 224, 224))]),
                                             outputs=Schema([TensorSpec(np.dtype("float32"), (-1, 4))])),
                                         registered_model_name=MLFLOW_REGISTERED_MODEL_NAME)
        summary.update(mlflow_run_id=run.info.run_id,
                       registered_model_name=MLFLOW_REGISTERED_MODEL_NAME,
                       registered_model_version=logged.registered_model_version)
        path.write_text(json.dumps(summary, indent=2) + "\n")
        mlflow.log_artifact(str(path), artifact_path="lineage")
        metadata_path = REPORTS_DIR / "model_metadata.json"
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text())
            if metadata.get("checkpoint_sha256") == summary["checkpoint_sha256"]:
                metadata.update(mlflow_run_id=run.info.run_id,
                                registered_model_name=MLFLOW_REGISTERED_MODEL_NAME,
                                registered_model_version=logged.registered_model_version)
                metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
                for artifact in (metadata_path, REPORTS_DIR / "model.onnx"):
                    mlflow.log_artifact(str(artifact), artifact_path="serving")
    print(f"Registered {MLFLOW_REGISTERED_MODEL_NAME} version {summary['registered_model_version']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--register", action="store_true")
    args = parser.parse_args()
    if args.source_dir:
        import_checkpoint(args.source_dir)
    if args.register:
        register_checkpoint()
    if not args.source_dir and not args.register:
        parser.error("Specify --source-dir or --register")
