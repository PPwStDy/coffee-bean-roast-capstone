"""Model Behaviour Tests for Coffee Bean Roast Classification.

Validates that model outputs satisfy physical and mathematical invariants,
independent of aggregate accuracy metrics.
"""
from __future__ import annotations

import time
import numpy as np
import pytest
import torch

from src.config import IMAGE_SIZE, LATENCY_BUDGET_MS, NUM_CLASSES, REPORTS_DIR, TORCHSCRIPT_MODEL_PATH
from src.model import build_model


@pytest.fixture(scope="session")
def loaded_model():
    """Require a real imported/trained model artifact."""
    if TORCHSCRIPT_MODEL_PATH.exists():
        model = torch.jit.load(str(TORCHSCRIPT_MODEL_PATH), map_location="cpu")
        model.eval()
        return model

    weights_path = REPORTS_DIR / "model_best.pth"
    if not weights_path.exists():
        pytest.fail("Missing model artifact; run make export")
    model = build_model(num_classes=NUM_CLASSES, pretrained=False)
    if weights_path.exists():
        model.load_state_dict(torch.load(weights_path, map_location="cpu", weights_only=True))
    model.eval()
    return model


def test_predictions_are_valid_probabilities(loaded_model):
    """Outputs must form a valid categorical distribution summing to 1.0 without NaNs."""
    dummy_input = torch.randn(1, 3, IMAGE_SIZE, IMAGE_SIZE)
    with torch.no_grad():
        logits = loaded_model(dummy_input)
        if isinstance(logits, tuple):
            logits = logits[0]
        probs = torch.softmax(logits, dim=1).numpy()[0]

    assert not np.isnan(probs).any(), "Probabilities contain NaN values"
    assert (probs >= 0.0).all(), f"Probabilities cannot be negative: {probs}"
    assert (probs <= 1.0).all(), f"Probabilities cannot exceed 1.0: {probs}"
    assert np.isclose(np.sum(probs), 1.0, atol=1e-4), f"Probabilities do not sum to 1.0: {np.sum(probs)}"


def test_prediction_latency_within_slo_budget(loaded_model):
    """In-process model evaluation must strictly satisfy the 120ms p95 latency SLO."""
    dummy_input = torch.randn(1, 3, IMAGE_SIZE, IMAGE_SIZE)

    # Warmup
    for _ in range(5):
        with torch.no_grad():
            _ = loaded_model(dummy_input)

    latencies = []
    for _ in range(25):
        t0 = time.perf_counter()
        with torch.no_grad():
            _ = loaded_model(dummy_input)
        latencies.append((time.perf_counter() - t0) * 1000)

    p95_latency = np.percentile(latencies, 95)
    assert p95_latency < LATENCY_BUDGET_MS, (
        f"p95 inference latency ({p95_latency:.2f} ms) exceeds SLO budget ({LATENCY_BUDGET_MS} ms)"
    )


def test_model_is_not_constant(loaded_model):
    """Model must produce non-trivial distinct predictions for distinct input patterns."""
    torch.manual_seed(123)
    input_a = torch.randn(1, 3, IMAGE_SIZE, IMAGE_SIZE)
    input_b = torch.randn(1, 3, IMAGE_SIZE, IMAGE_SIZE) * 2.0 + 1.0

    with torch.no_grad():
        out_a = torch.softmax(loaded_model(input_a), dim=1).numpy()[0]
        out_b = torch.softmax(loaded_model(input_b), dim=1).numpy()[0]

    # Predictions must not be numerically identical
    diff = np.abs(out_a - out_b).sum()
    assert diff > 1e-4, "Model produced identical outputs for contrasting inputs (collapsed/constant model)"


def test_inference_is_deterministic(loaded_model):
    """Identical input tensors must yield identical output distributions."""
    input_tensor = torch.randn(1, 3, IMAGE_SIZE, IMAGE_SIZE)
    with torch.no_grad():
        out_1 = loaded_model(input_tensor).numpy()
        out_2 = loaded_model(input_tensor).numpy()
    np.testing.assert_allclose(out_1, out_2, atol=1e-5)
