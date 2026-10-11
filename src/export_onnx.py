"""Export the imported or retrained Swin model with a checked four-class serving contract."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
import numpy as np
import torch
from src.config import (ARCHITECTURE, CLASSES, DATA_DIR, IMAGE_SIZE, IMPORTED_CHECKPOINT_PATH,
                        LATENCY_BUDGET_MS, MODEL_METADATA_PATH, MODEL_PATH, REPORTS_DIR,
                        TORCHSCRIPT_MODEL_PATH)
from src.data import get_eval_transforms
from src.model import build_model
from PIL import Image


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def export_models(weights_path: Path | None = None, quantize: bool = True):
    if weights_path is None:
        trained = REPORTS_DIR / "model_best.pth"
        weights_path = trained if trained.exists() else IMPORTED_CHECKPOINT_PATH
    weights_path = Path(weights_path).resolve()
    lineage_path = (REPORTS_DIR / "iteration4_import.json" if weights_path == IMPORTED_CHECKPOINT_PATH
                    else REPORTS_DIR / "training_summary.json")
    if not weights_path.exists() or not lineage_path.exists():
        raise FileNotFoundError("Import the Iteration4 checkpoint or run make train before exporting")
    lineage = json.loads(lineage_path.read_text())
    if lineage["classes"] != CLASSES or lineage["architecture"] != ARCHITECTURE:
        raise ValueError("Checkpoint lineage does not match the roast/Swin model contract")
    if lineage.get("checkpoint_sha256") != sha256(weights_path):
        raise ValueError("Checkpoint content does not match its recorded lineage")
    torch.set_num_threads(int(os.environ.get("INFERENCE_THREADS", "1")))
    torch.manual_seed(42)
    model = build_model(pretrained=False).eval()
    model.load_state_dict(torch.load(weights_path, map_location="cpu", weights_only=True), strict=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    TORCHSCRIPT_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    dummy = torch.randn(1, 3, IMAGE_SIZE, IMAGE_SIZE)
    # Script preserves Swin's batch-dependent operations and avoids tracing shape branches.
    scripted = torch.jit.script(model)
    scripted.save(str(TORCHSCRIPT_MODEL_PATH))
    float_path = REPORTS_DIR / "model.float.onnx"
    torch.onnx.export(model, dummy, str(float_path), opset_version=17, dynamo=False,
                      input_names=["input"], output_names=["output"],
                      dynamic_axes={"input": {0: "batch_size"}, "output": {0: "batch_size"}})
    if quantize:
        from onnxruntime.quantization import QuantType, quantize_dynamic
        # Restrict to dense weights; quantizing the patch Conv can create unsupported ConvInteger.
        quantize_dynamic(str(float_path), str(MODEL_PATH), weight_type=QuantType.QInt8,
                         op_types_to_quantize=["MatMul", "Gemm"], per_channel=True)
    else:
        import shutil
        shutil.copy2(float_path, MODEL_PATH)

    import onnxruntime as ort
    options = ort.SessionOptions()
    options.intra_op_num_threads = int(os.environ.get("INFERENCE_THREADS", "1"))
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(MODEL_PATH), sess_options=options, providers=["CPUExecutionProvider"])
    samples = [dummy]
    transform = get_eval_transforms()
    for label in CLASSES:
        for path in sorted((DATA_DIR / "test" / label).glob("*.png"))[:2]:
            with Image.open(path) as image:
                samples.append(transform(image.convert("RGB")).unsqueeze(0))
    max_probability_error = 0.0
    for sample in samples:
        with torch.inference_mode():
            baseline = model(sample)
            ts_out = scripted(sample)
        np.testing.assert_allclose(baseline.numpy(), ts_out.numpy(), rtol=1e-4, atol=1e-4)
        ort_out = session.run(None, {"input": sample.numpy()})[0]
        if ort_out.shape != (1, len(CLASSES)) or not np.isfinite(ort_out).all():
            raise ValueError(f"Invalid exported output: {ort_out}")
        baseline_probs = torch.softmax(baseline, dim=1).numpy()
        ort_probs = torch.softmax(torch.from_numpy(ort_out), dim=1).numpy()
        max_probability_error = max(max_probability_error, float(np.max(np.abs(baseline_probs - ort_probs))))
        np.testing.assert_allclose(baseline_probs, ort_probs, atol=0.05, rtol=0)
        if baseline_probs.argmax() != ort_probs.argmax():
            raise ValueError("ONNX export changed the predicted class; export without quantization")
    for _ in range(5):
        session.run(None, {"input": dummy.numpy()})
    latencies = []
    for _ in range(30):
        started = time.perf_counter()
        session.run(None, {"input": dummy.numpy()})
        latencies.append((time.perf_counter() - started) * 1000)
    metadata = {
        **lineage, "input_size": IMAGE_SIZE, "normalization": "ImageNet",
        "quantization": "dynamic_int8_dense_weights" if quantize else "float32",
        "onnx_sha256": sha256(MODEL_PATH), "torchscript_sha256": sha256(TORCHSCRIPT_MODEL_PATH),
        "onnx_size_mib": MODEL_PATH.stat().st_size / (1024**2),
        "parity_samples": len(samples), "max_probability_error": max_probability_error,
        "local_cpu_latency_p50_ms": float(np.percentile(latencies, 50)),
        "local_cpu_latency_p95_ms": float(np.percentile(latencies, 95)),
        "latency_target_ms": LATENCY_BUDGET_MS,
        "latency_target_met_locally": bool(np.percentile(latencies, 95) <= LATENCY_BUDGET_MS),
        "inference_threads": options.intra_op_num_threads,
        "onnxruntime_version": ort.__version__,
        "torch_version": torch.__version__,
        "numpy_version": np.__version__,
    }
    MODEL_METADATA_PATH.write_text(json.dumps(metadata, indent=2) + "\n")
    float_path.unlink(missing_ok=True)
    print(json.dumps(metadata, indent=2))
    # Export stays usable when hardware misses an SLO; the explicit load-test gate enforces it.
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path)
    parser.add_argument("--no-quantize", action="store_true")
    args = parser.parse_args()
    export_models(args.weights, quantize=not args.no_quantize)
