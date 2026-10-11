"""Fixed targets require the complete measured protocol and cannot be recalibrated."""

import json
from pathlib import Path

import pytest

from loadtest.bench import enforce, freeze


def evidence():
    warm = dict(
        requests=1000,
        concurrency=2,
        successful_requests=1000,
        p95_ms=226.65,
        p99_ms=251.16,
        model_version="test-v1",
        client_origin="github-actions-ubuntu",
    )
    cold = dict(
        p95_ms=10000.1,
        p99_ms=12000.1,
        trials=[dict(replicas_before_request=0, status=200) for _ in range(20)],
    )
    return warm, cold


def test_freeze_margin_and_refuse_recalibration(tmp_path):
    warm, cold = evidence()
    path = tmp_path / "slo.json"
    targets = freeze(warm, cold, 123456, path)
    assert [targets[k] for k in ("warm_p95_ms", "warm_p99_ms", "cold_p95_ms", "cold_p99_ms")] == [
        272,
        302,
        12001,
        14401,
    ]
    assert targets["container_size_bytes"] == 123456
    with pytest.raises(FileExistsError):
        freeze(warm, cold, 123456, path)


@pytest.mark.parametrize("missing", ["warm", "cold", "zero"])
def test_incomplete_measurement_cannot_freeze(tmp_path, missing):
    warm, cold = evidence()
    if missing == "warm":
        warm["requests"] = 999
    elif missing == "cold":
        cold["trials"].pop()
    else:
        cold["trials"][0]["replicas_before_request"] = 1
    with pytest.raises(ValueError):
        freeze(warm, cold, 123456, tmp_path / "slo.json")


def test_fixed_release_gate_checks_origin_and_percentiles(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("monitoring").mkdir()
    warm, cold = evidence()
    freeze(warm, cold, 123456)
    enforce(warm)
    wrong_origin = {**warm, "client_origin": "local-mac-bangkok"}
    with pytest.raises(AssertionError, match="origin"):
        enforce(wrong_origin)
    targets = json.loads(Path("monitoring/slo.json").read_text())
    with pytest.raises(AssertionError, match="p95"):
        enforce({**warm, "p95_ms": targets["warm_p95_ms"] + 1})
    with pytest.raises(AssertionError, match="p99"):
        enforce({**warm, "p99_ms": targets["warm_p99_ms"] + 1})
