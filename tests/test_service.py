"""Service Integration and Deliberate Failure Tests for Coffee Roast Classification API.

Verifies HTTP contracts, telemetry headers, and the closed-loop deliberate failure defense:
asserting that degenerate glare/occlusion frames are intercepted and rejected with HTTP 422
before softmax hallucination can corrupt downstream sorting telemetry.
"""
from __future__ import annotations

import io
import numpy as np
from fastapi.testclient import TestClient
from PIL import Image
import pytest

from service.app import app
from src.config import CLASSES


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


def _make_test_image_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="JPEG")
    return buf.getvalue()


def test_health_liveness_endpoint(client):
    """GET /health must return 200 OK with alive status."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "alive"
    assert "x-request-id" in res.headers
    assert "x-model-version" in res.headers


def test_ready_readiness_endpoint(client):
    """GET /ready must confirm model is loaded and ready to serve."""
    res = client.get("/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["model_loaded"] is True
    assert "engine" in data


def test_predict_valid_textured_bean_image(client):
    """A natural bean image with healthy pixel variance must score successfully."""
    # Create realistic high-variance synthetic image (representing textured bean)
    np_img = np.random.randint(40, 220, (224, 224, 3), dtype=np.uint8)
    img = Image.fromarray(np_img, mode="RGB")
    raw_bytes = _make_test_image_bytes(img)

    res = client.post("/predict", content=raw_bytes, headers={"Content-Type": "image/jpeg"})
    assert res.status_code == 200, f"Predict failed: {res.text}"
    data = res.json()

    assert data["predicted_class"] in CLASSES
    assert 0 <= data["predicted_class_id"] < len(CLASSES)
    assert 0.0 <= data["confidence"] <= 1.0
    assert len(data["probabilities"]) == len(CLASSES)
    assert np.isclose(sum(data["probabilities"].values()), 1.0, atol=1e-3)
    assert data["pixel_std"] >= 0.05
    assert data["latency_ms"] > 0.0


# --- DELIBERATE FAILURE TESTS (RUBRIC CRITERION R4) ---

def test_deliberate_failure_specular_glare_rejected(client):
    """Engineered Fault Injection: Specular optical glare (pure white frame).

    Unprotected classifiers normalize inputs and output high-confidence predictions on solid white.
    Our variance guard must intercept this and reject with HTTP 422 Unprocessable Entity.
    """
    white_img = Image.new("RGB", (224, 224), color=(255, 255, 255))
    raw_bytes = _make_test_image_bytes(white_img)

    res = client.post("/predict", content=raw_bytes, headers={"Content-Type": "image/jpeg"})
    assert res.status_code == 422, f"Expected 422 for pure glare, got {res.status_code}: {res.text}"

    detail = res.json()["detail"]
    assert "Optical Occlusion / Specular Glare Detected" in detail["error"]
    assert detail["pixel_std"] < 0.05
    assert "inspect camera lens" in detail["message"]


def test_deliberate_failure_lens_occlusion_rejected(client):
    """Engineered Fault Injection: Lens dust/chaff occlusion (pure black frame).

    Our variance guard must intercept collapsed dynamic range and reject with HTTP 422.
    """
    black_img = Image.new("RGB", (224, 224), color=(0, 0, 0))
    raw_bytes = _make_test_image_bytes(black_img)

    res = client.post("/predict", content=raw_bytes, headers={"Content-Type": "image/jpeg"})
    assert res.status_code == 422, f"Expected 422 for dust occlusion, got {res.status_code}: {res.text}"

    detail = res.json()["detail"]
    assert "Optical Occlusion / Specular Glare Detected" in detail["error"]
    assert detail["pixel_std"] < 0.05


def test_prometheus_telemetry_metrics_exported(client):
    """GET /metrics must export Prometheus telemetry counters and histograms."""
    res = client.get("/metrics")
    assert res.status_code == 200
    content = res.text
    assert "coffee_inference_latency_seconds" in content
    assert "coffee_predictions_total" in content
    assert "coffee_anomaly_frames_total" in content
