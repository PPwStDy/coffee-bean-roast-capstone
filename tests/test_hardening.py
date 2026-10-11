"""Payload, optical guard, readiness, logs and serving contract regressions."""

import base64
import io
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import service.app as service
from src.config import CLASSES


@pytest.fixture
def client():
    with TestClient(service.app) as client:
        yield client


def image_bytes(color=0, size=(224, 224), format="PNG"):
    stream = io.BytesIO()
    Image.new("RGB", size, color).save(stream, format=format)
    return stream.getvalue()


@pytest.mark.parametrize("color", [0, 255])
def test_optical_guard_precedes_inference(client, monkeypatch, color):
    def forbidden(_):
        pytest.fail("Optically rejected frame reached the model")

    monkeypatch.setattr(service, "run_inference", forbidden)
    response = client.post("/predict", content=image_bytes(color), headers={"content-type": "image/png"})
    assert response.status_code == 422
    assert "Optical Occlusion" in response.json()["detail"]["error"]


@pytest.mark.parametrize("payload,status", [(b"", 400), (b"garbage", 400), (b"x" * (5 * 1024**2 + 1), 413)])
def test_bad_raw_payloads(client, payload, status):
    assert (
        client.post("/predict", content=payload, headers={"content-type": "image/png"}).status_code == status
    )


def test_pixel_limit_and_unsupported_format(client):
    assert (
        client.post(
            "/predict", content=image_bytes(size=(5000, 4001)), headers={"content-type": "image/png"}
        ).status_code
        == 413
    )
    assert (
        client.post(
            "/predict",
            content=image_bytes(format="GIF"),
            headers={"content-type": "application/octet-stream"},
        ).status_code
        == 415
    )
    assert client.post("/predict", content=b"data", headers={"content-type": "text/plain"}).status_code == 415


@pytest.mark.parametrize(
    "payload,status",
    [
        ({"image_base64": "%%%"}, 400),
        ({"image_base64": "YQ"}, 400),
        ({"image_base64": ""}, 400),
        ({}, 422),
        ({"image_base64": 42}, 422),
    ],
)
def test_bad_base64(client, payload, status):
    assert client.post("/predict/base64", json=payload).status_code == status


def assert_prediction(response):
    assert response.status_code == 200, response.text
    result = response.json()
    assert list(result["probabilities"]) == CLASSES
    assert CLASSES[result["predicted_class_id"]] == result["predicted_class"]
    assert all(0 <= p <= 1 for p in result["probabilities"].values())
    assert abs(sum(result["probabilities"].values()) - 1) < 0.001
    assert result["model_version"] == response.headers["x-model-version"]


def test_raw_multipart_base64_and_concurrency(client):
    image = Path("tests/fixtures/Dark.png").read_bytes()
    assert_prediction(client.post("/predict/base64", json={"image_base64": base64.b64encode(image).decode()}))
    assert_prediction(client.post("/predict", files={"file": ("bean.png", image, "image/png")}))
    with ThreadPoolExecutor(max_workers=2) as pool:
        for response in pool.map(
            lambda _: client.post("/predict", content=image, headers={"content-type": "image/png"}), range(8)
        ):
            assert_prediction(response)


def test_json_logs_escape_untrusted_values():
    import logging

    formatter = service.JSONFormatter()
    record = logging.LogRecord(
        "test", 20, "file", 1, json.dumps({"request_id": 'quote"\\\n', "event": "http_request"}), (), None
    )
    assert json.loads(formatter.format(record))["request_id"] == 'quote"\\\n'


@pytest.mark.parametrize("fault", ["missing", "corrupt", "classes", "preprocessing", "version"])
def test_artifact_faults_fail_readiness(monkeypatch, tmp_path, fault):
    metadata = json.loads(service.MODEL_METADATA_PATH.read_text())
    path = tmp_path / "metadata.json"
    if fault == "classes":
        metadata["classes"] = list(reversed(CLASSES))
    elif fault == "preprocessing":
        metadata["preprocessing"] = {"resize": "nearest"}
    elif fault == "version":
        monkeypatch.setenv("MODEL_VERSION", "incompatible-version")
    elif fault == "missing":
        monkeypatch.setenv("MODEL_PATH", str(tmp_path / "missing.onnx"))
    elif fault == "corrupt":
        artifact = tmp_path / "bad.onnx"
        artifact.write_bytes(b"corrupted")
        monkeypatch.setenv("MODEL_PATH", str(artifact))
    path.write_text(json.dumps(metadata))
    monkeypatch.setattr(service, "MODEL_METADATA_PATH", path)
    with TestClient(service.app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 503
        assert (
            client.post("/predict", content=Path("tests/fixtures/Dark.png").read_bytes()).status_code == 503
        )
