"""Select a serving export on validation data; evaluate a selected clean release once."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch
from PIL import Image
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from onnxruntime.quantization import QuantType, quantize_dynamic

from src.config import (
    ARCHITECTURE,
    CLASSES,
    DATA_DIR,
    IMAGE_SIZE,
    IMPORTED_CHECKPOINT_PATH,
    MODEL_METADATA_PATH,
    MODEL_PATH,
    REPORTS_DIR,
    ROOT_DIR,
    TORCHSCRIPT_MODEL_PATH,
)
from src.data import get_eval_transforms, validate_dataset
from src.model import build_model


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def session_for(path):
    options = ort.SessionOptions()
    options.intra_op_num_threads = int(os.environ.get("INFERENCE_THREADS", "1"))
    options.inter_op_num_threads = 1
    return ort.InferenceSession(str(path), sess_options=options, providers=["CPUExecutionProvider"])


def samples(split):
    transform = get_eval_transforms()
    for index, label in enumerate(CLASSES):
        for path in sorted((DATA_DIR / split / label).glob("*.png")):
            with Image.open(path) as image:
                yield transform(image.convert("RGB")).unsqueeze(0).numpy(), index


def evaluate_export(session, split):
    targets, predictions, timings = [], [], []
    for batch, target in samples(split):
        started = time.perf_counter()
        logits = session.run(None, {"input": batch})[0]
        timings.append((time.perf_counter() - started) * 1000)
        if logits.shape != (1, len(CLASSES)) or not np.isfinite(logits).all():
            raise ValueError("Export produced incompatible or nonfinite logits")
        targets.append(target)
        predictions.append(int(logits.argmax()))
    return {
        "split": split,
        "count": len(targets),
        "accuracy": float(np.mean(np.array(targets) == predictions)),
        "macro_f1": float(f1_score(targets, predictions, labels=range(4), average="macro", zero_division=0)),
        "latency_p50_ms": float(np.percentile(timings, 50)),
        "latency_p95_ms": float(np.percentile(timings, 95)),
        "classification_report": classification_report(
            targets, predictions, labels=range(4), target_names=CLASSES, zero_division=0, output_dict=True
        ),
        "confusion_matrix": confusion_matrix(targets, predictions, labels=range(4)).tolist(),
    }


def export_models(weights_path=None, quantize=True, evaluate_test=False):
    validate_dataset()
    weights_path = Path(weights_path or (REPORTS_DIR / "model_best.pth")).resolve()
    baseline = weights_path == IMPORTED_CHECKPOINT_PATH.resolve()
    lineage_path = REPORTS_DIR / ("iteration4_import.json" if baseline else "training_summary.json")
    lineage = json.loads(lineage_path.read_text())
    if lineage["classes"] != CLASSES or lineage["architecture"] != ARCHITECTURE:
        raise ValueError("Checkpoint lineage violates the class/architecture contract")
    if lineage["checkpoint_sha256"] != sha256(weights_path):
        raise ValueError("Checkpoint content differs from lineage")
    if evaluate_test and baseline:
        raise ValueError("Historical contaminated checkpoint cannot receive a clean test evaluation")
    version = lineage["model_version"]
    release = ROOT_DIR / "releases" / version
    if evaluate_test and release.exists():
        raise FileExistsError("Release already exists: test evaluation is immutable and must not be repeated")
    torch.set_num_threads(int(os.environ.get("INFERENCE_THREADS", "1")))
    torch.manual_seed(42)
    model = build_model(pretrained=False).eval()
    model.load_state_dict(torch.load(weights_path, map_location="cpu", weights_only=True), strict=True)
    dummy = torch.randn(1, 3, IMAGE_SIZE, IMAGE_SIZE)
    scripted = torch.jit.script(model)
    scripted.save(str(TORCHSCRIPT_MODEL_PATH))
    float_path, int8_path = REPORTS_DIR / "model.float.onnx", REPORTS_DIR / "model.int8.onnx"
    torch.onnx.export(
        model,
        dummy,
        str(float_path),
        opset_version=17,
        dynamo=False,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
    )
    if quantize:
        quantize_dynamic(
            str(float_path),
            str(int8_path),
            weight_type=QuantType.QInt8,
            op_types_to_quantize=["MatMul", "Gemm"],
            per_channel=True,
        )
    candidates = []
    for name, path in [("float32", float_path)] + (
        [("dynamic_int8_dense_weights", int8_path)] if quantize else []
    ):
        session = session_for(path)
        for _ in range(5):
            session.run(None, {"input": dummy.numpy()})
        result = {
            "quantization": name,
            "sha256": sha256(path),
            "size_mib": path.stat().st_size / 1024**2,
            **evaluate_export(session, "valid"),
        }
        errors = []
        for batch, _ in list(samples("valid"))[::22]:
            with torch.inference_mode():
                reference = model(torch.from_numpy(batch))
                np.testing.assert_allclose(
                    reference.numpy(), scripted(torch.from_numpy(batch)).numpy(), atol=1e-4, rtol=1e-4
                )
            exported = session.run(None, {"input": batch})[0]
            expected = torch.softmax(reference, dim=1).numpy()
            actual = torch.softmax(torch.from_numpy(exported), dim=1).numpy()
            errors.append(float(np.max(np.abs(actual - expected))))
        result["max_probability_error"] = max(errors)
        result["parity_samples"] = len(errors)
        candidates.append(result)
    float_f1 = candidates[0]["macro_f1"]
    eligible = [
        c
        for c in candidates
        if c["macro_f1"] >= float_f1 - 0.01 - 1e-12 and c["max_probability_error"] <= 0.05
    ]
    if not eligible:
        raise ValueError("No export passed the validation F1 and parity gates")
    selected = min(eligible, key=lambda c: c["latency_p50_ms"])
    selected_path = float_path if selected["quantization"] == "float32" else int8_path
    shutil.copy2(selected_path, MODEL_PATH)
    metadata = {
        **lineage,
        "input_size": IMAGE_SIZE,
        "normalization": "ImageNet",
        "classes": CLASSES,
        "preprocessing": {"resize": "bilinear", "mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225]},
        "onnx_sha256": sha256(MODEL_PATH),
        "torchscript_sha256": sha256(TORCHSCRIPT_MODEL_PATH),
        "onnx_size_mib": MODEL_PATH.stat().st_size / 1024**2,
        "quantization": selected["quantization"],
        "validation_candidates": candidates,
        "selection": "fastest validation median among <=1 percentage-point macro-F1 loss and <=.05 probability error",
        "export_code_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "onnxruntime_version": ort.__version__,
        "inference_threads": 1,
    }
    (REPORTS_DIR / "export_candidates.json").write_text(json.dumps(candidates, indent=2) + "\n")
    if evaluate_test:
        release.mkdir(parents=True)
        # Persist the attempt BEFORE reading any test images; interruptions cannot silently repeat evaluation.
        (release / "test_evaluation_started.json").write_text(
            json.dumps({"onnx_sha256": metadata["onnx_sha256"], "time": time.time()}) + "\n"
        )
        evaluation = evaluate_export(session_for(MODEL_PATH), "test")
        metadata["test_evaluation"] = evaluation
        (release / "evaluation.json").write_text(json.dumps(evaluation, indent=2) + "\n")
        shutil.copy2(weights_path, release / "checkpoint.pth")
        shutil.copy2(MODEL_PATH, release / "model.onnx")
        shutil.copy2(TORCHSCRIPT_MODEL_PATH, release / "model.pt")
        shutil.copy2(REPORTS_DIR / "training_history.json", release / "training_history.json")
        card = (
            f"# Model card: {version}\n\nSwin-T; Dark, Green, Light, Medium. RGB224, ImageNet normalization.\n\n"
            f"Training: {lineage['code_revision']}; dataset {lineage['dataset_dvc_hash']}; seed42, ImageNet initialization.\n\n"
            f"Selected export: {selected['quantization']}; held-out test n={evaluation['count']}, "
            f"accuracy={evaluation['accuracy']:.4f}, macro-F1={evaluation['macro_f1']:.4f}.\n\n"
            "Intended use: educational image-level roast classification, never individual-bean defect grading. "
            "CC BY-SA4 dataset; see DATA_LICENSE.md. Different origins and camera conditions can confound labels. "
            "Confidence is uncalibrated. Solid frames rejected optically; arbitrary out-of-domain images can pass. "
            "Original Iteration4 baseline saw all original test images and is unsuitable for generalization claims.\n"
        )
        (release / "model_card.md").write_text(card)
        (REPORTS_DIR / "model_card.md").write_text(card)
        (release / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
        manifest = {p.name: sha256(p) for p in release.iterdir() if p.is_file()}
        (release / "sha256.json").write_text(json.dumps(manifest, indent=2) + "\n")
    MODEL_METADATA_PATH.write_text(json.dumps(metadata, indent=2) + "\n")
    print(
        json.dumps(
            {
                "model_version": version,
                "selected": selected["quantization"],
                "test": metadata.get("test_evaluation"),
            },
            indent=2,
        )
    )
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path)
    parser.add_argument("--no-quantize", action="store_true")
    parser.add_argument("--evaluate-test", action="store_true")
    args = parser.parse_args()
    export_models(args.weights, quantize=not args.no_quantize, evaluate_test=args.evaluate_test)
