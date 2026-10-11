"""Remove the optical guard in an isolated copy and require its regression test to fail."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="coffee-guard-drill-") as folder:
    target = Path(folder)
    for name in ["src", "service", "tests"]:
        shutil.copytree(root / name, target / name, ignore=shutil.ignore_patterns("__pycache__"))
    app = target / "service/app.py"
    source = app.read_text()
    needle = "pixel_std, entropy = validate_frame_quality(image)"
    if source.count(needle) != 1:
        raise ValueError("Guard call cannot be mutated unambiguously")
    app.write_text(source.replace(needle, "pixel_std, entropy = 0.2, 7.0"))
    environment = {
        **os.environ,
        "PYTHONPATH": str(target),
        "MODEL_PATH": str(root / "reports/model.onnx"),
        "MODEL_METADATA_PATH": str(root / "reports/model_metadata.json"),
        "TORCHSCRIPT_MODEL_PATH": str(root / "reports/model.pt"),
    }
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_hardening.py::test_optical_guard_precedes_inference",
            "-q",
        ],
        cwd=target,
        env=environment,
        capture_output=True,
        text=True,
    )
    evidence = {
        "mutation": "optical guard call removed in temporary source copy",
        "exit_code": result.returncode,
        "regression_caught": result.returncode == 1
        and "Optically rejected frame reached the model" in result.stdout,
        "output": result.stdout + result.stderr,
    }
    (root / "reports/evidence/optical-regression-drill.json").write_text(
        json.dumps(evidence, indent=2) + "\n"
    )
    print(json.dumps({k: v for k, v in evidence.items() if k != "output"}))
    if not evidence["regression_caught"]:
        raise SystemExit("Mutated optical guard did not cause the expected regression failures")
