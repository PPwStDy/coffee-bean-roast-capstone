"""Acceptance checks shared by container integration and candidate promotion."""

import argparse
import base64
import io
import json
import time
from pathlib import Path

import httpx
from PIL import Image

CLASSES = ["Dark", "Green", "Light", "Medium"]


def check(url, version=None):
    results = []
    with httpx.Client(base_url=url, timeout=180) as client:
        deadline = time.monotonic() + 300
        while True:
            try:
                response = client.get("/ready")
                if response.status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            if time.monotonic() > deadline:
                raise TimeoutError("Endpoint did not become ready in five minutes")
            time.sleep(5)
        loaded_version = response.json()["model_version"]
        if version and loaded_version != version:
            raise AssertionError("Candidate version differs from release metadata")
        for label in CLASSES:
            image = Path("tests/fixtures", label + ".png").read_bytes()
            response = client.post("/predict", content=image, headers={"content-type": "image/png"})
            assert response.status_code == 200, response.text
            result = response.json()
            assert list(result["probabilities"]) == CLASSES
            assert all(0 <= value <= 1 for value in result["probabilities"].values())
            assert abs(sum(result["probabilities"].values()) - 1) < 0.001
            assert CLASSES[result["predicted_class_id"]] == result["predicted_class"]
            assert response.headers["x-model-version"] == result["model_version"] == loaded_version
            results.append({"fixture": label, "status": response.status_code, "result": result})
        response = client.post("/predict/base64", json={"image_base64": base64.b64encode(image).decode()})
        assert response.status_code == 200
        for name, color in [("black", (0, 0, 0)), ("white", (255, 255, 255))]:
            stream = io.BytesIO()
            Image.new("RGB", (224, 224), color).save(stream, "PNG")
            response = client.post(
                "/predict", content=stream.getvalue(), headers={"content-type": "image/png"}
            )
            assert response.status_code == 422, response.text
            results.append({"fault": name, "status": 422, "response": response.json()})
        assert (
            client.post("/predict", content=b"bad", headers={"content-type": "image/png"}).status_code == 400
        )
        assert client.post("/predict/base64", json={"image_base64": "%%%"}).status_code == 400
        metrics = client.get("/metrics")
        assert metrics.status_code == 200
        assert 'coffee_anomaly_frames_total{rejection_reason="low_variance_occlusion"}' in metrics.text
        assert "coffee_http_errors_total" in metrics.text
    return {"url": url, "model_version": loaded_version, "checks": results, "passed": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--version")
    parser.add_argument("--output", default="reports/evidence/endpoint-checks.json")
    args = parser.parse_args()
    result = check(args.url, args.version)
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": True, "url": args.url, "version": result["model_version"]}))
