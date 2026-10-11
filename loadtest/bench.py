"""Real HTTP warm benchmark. Freeze targets explicitly once; never silently recalibrate."""

import argparse
import json
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import httpx
import numpy as np


def benchmark(url, requests=1000, concurrency=2):
    images = [p.read_bytes() for p in sorted(Path("tests/fixtures").glob("*.png"))]
    if not images:
        raise ValueError("Licensed validation fixtures are missing")
    with httpx.Client(timeout=180, limits=httpx.Limits(max_connections=concurrency)) as client:
        for image in images:
            response = client.post(
                url.rstrip("/") + "/predict", content=image, headers={"content-type": "image/png"}
            )
            response.raise_for_status()

        def request(index):
            started = time.perf_counter()
            response = client.post(
                url.rstrip("/") + "/predict",
                content=images[index % len(images)],
                headers={"content-type": "image/png"},
            )
            elapsed = (time.perf_counter() - started) * 1000
            if response.status_code != 200:
                raise AssertionError(f"Request {index}: {response.status_code} {response.text}")
            result = response.json()
            assert len(result["probabilities"]) == 4 and all(
                math.isfinite(v) for v in result["probabilities"].values()
            )
            assert abs(sum(result["probabilities"].values()) - 1) < 0.001
            assert response.headers["x-model-version"] == result["model_version"]
            return elapsed, result["latency_ms"], result["model_version"]

        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            samples = list(pool.map(request, range(requests)))
        duration = time.perf_counter() - started
    versions = {r[2] for r in samples}
    if len(versions) != 1:
        raise AssertionError("Benchmark crossed model versions")
    return {
        "client_origin": "github-actions-ubuntu" if os.environ.get("GITHUB_ACTIONS") else "local-mac-bangkok",
        "url": url,
        "requests": requests,
        "concurrency": concurrency,
        "successful_requests": len(samples),
        "model_version": versions.pop(),
        "duration_seconds": duration,
        "requests_per_second": requests / duration,
        "p50_ms": float(np.percentile([r[0] for r in samples], 50)),
        "p95_ms": float(np.percentile([r[0] for r in samples], 95)),
        "p99_ms": float(np.percentile([r[0] for r in samples], 99)),
        "server_p95_ms": float(np.percentile([r[1] for r in samples], 95)),
        "latencies_ms": [r[0] for r in samples],
    }


def freeze(report, cold, container_bytes, path=Path("monitoring/slo.json")):
    if path.exists():
        raise FileExistsError("Initial targets already frozen; recalibration is forbidden")
    if (
        report["requests"] != 1000
        or report["successful_requests"] != 1000
        or report["concurrency"] != 2
        or len(cold["trials"]) != 20
    ):
        raise ValueError(
            "Target freeze requires 1000 warm requests at concurrency two and 20 proven cold starts"
        )
    if not all(t["replicas_before_request"] == 0 and t["status"] == 200 for t in cold["trials"]):
        raise ValueError("Cold trials must establish zero replicas and successful responses")
    targets = {
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "warm_p95_ms": math.ceil(report["p95_ms"] * 1.2),
        "warm_p99_ms": math.ceil(report["p99_ms"] * 1.2),
        "cold_p95_ms": math.ceil(cold["p95_ms"] * 1.2),
        "cold_p99_ms": math.ceil(cold["p99_ms"] * 1.2),
        "container_size_bytes": container_bytes,
        "model_version": report["model_version"],
        "method": "initial measured percentile +20%, rounded upward; container size separate",
        "warm_client_origin": report.get("client_origin", "local-mac-bangkok"),
        "warm_evidence": "reports/evidence/initial-warm.json",
        "cold_evidence": "reports/evidence/initial-cold.json",
    }
    path.write_text(json.dumps(targets, indent=2) + "\n")
    return targets


def enforce(report):
    targets = json.loads(Path("monitoring/slo.json").read_text())
    assert report.get("client_origin", "local-mac-bangkok") == targets["warm_client_origin"], (
        "Benchmark client origin differs from the frozen baseline"
    )
    assert report["successful_requests"] == report["requests"]
    assert report["p95_ms"] <= targets["warm_p95_ms"], "Frozen p95 target exceeded"
    assert report["p99_ms"] <= targets["warm_p99_ms"], "Frozen p99 target exceeded"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--requests", type=int, default=1000)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--output", default="reports/evidence/deployed-warm.json")
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()
    report = benchmark(args.url, args.requests, args.concurrency)
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
    if args.enforce:
        enforce(report)
    print(json.dumps({k: v for k, v in report.items() if k != "latencies_ms"}, indent=2))
