"""Measure real scale-to-zero cold starts; no probe may wake the app between trials."""

import argparse
import json
import time
import math
from datetime import datetime, timezone
from pathlib import Path

import httpx
import numpy as np
from cloudlayer.cli import az
from cloudlayer.config import settings


def measure(url, trials=20):
    config = settings()
    app = config["ENDPOINT_NAME"]
    group = config["PROJECT_ID"]
    image = Path("tests/fixtures/Dark.png").read_bytes()
    progress = Path("reports/evidence/cold-start-progress.json")
    results = json.loads(progress.read_text()) if progress.exists() else []
    expected_version = json.loads(Path("reports/model_metadata.json").read_text())["model_version"]
    if any(
        t["model_version"] != expected_version or t["replicas_before_request"] != 0 or t["status"] != 200
        for t in results
    ):
        raise ValueError("Saved cold evidence is incompatible with this release")
    if len(results) > trials:
        raise ValueError("Saved evidence exceeds the requested trial count")
    for index in range(len(results), trials):
        # This waits for natural HTTP cooldown; management-plane queries do not wake serving replicas.
        wait_started = time.monotonic()
        deadline = wait_started + 1800
        while True:
            revisions = az("containerapp", "revision", "list", "--name", app, "--resource-group", group)
            active = [r["name"] for r in revisions if r["properties"].get("active")]
            replicas = []
            for revision in active:
                replicas.extend(
                    az(
                        "containerapp",
                        "replica",
                        "list",
                        "--name",
                        app,
                        "--resource-group",
                        group,
                        "--revision",
                        revision,
                    )
                )
            if not replicas:
                zero_verified_at = datetime.now(timezone.utc).isoformat()
                break
            if time.monotonic() > deadline:
                raise TimeoutError("App did not scale to zero; disable external scrapers/health polling")
            time.sleep(30)
        started = time.perf_counter()
        response = httpx.post(
            url.rstrip("/") + "/predict", content=image, headers={"content-type": "image/png"}, timeout=300
        )
        elapsed = (time.perf_counter() - started) * 1000
        response.raise_for_status()
        body = response.json()
        assert response.headers["x-model-version"] == body["model_version"] == expected_version
        probabilities = body["probabilities"]
        assert list(probabilities) == ["Dark", "Green", "Light", "Medium"]
        assert all(math.isfinite(v) and 0 <= v <= 1 for v in probabilities.values())
        assert abs(sum(probabilities.values()) - 1) < 0.001
        assert list(probabilities)[body["predicted_class_id"]] == body["predicted_class"]
        results.append(
            {
                "trial": index + 1,
                "replicas_before_request": 0,
                "zero_verified_at": zero_verified_at,
                "active_revisions": active,
                "management_replica_response": replicas,
                "wait_for_zero_seconds": time.monotonic() - wait_started - elapsed / 1000,
                "status": response.status_code,
                "latency_ms": elapsed,
                "model_version": response.json()["model_version"],
            }
        )
        progress.write_text(json.dumps(results, indent=2) + "\n")
        print(f"Cold trial {index + 1}/{trials}: {elapsed:.0f} ms", flush=True)
    return {
        "url": url,
        "method": "natural HTTP scale-to-zero; zero replicas verified by management-plane API",
        "trials": results,
        "p95_ms": float(np.percentile([r["latency_ms"] for r in results], 95)),
        "p99_ms": float(np.percentile([r["latency_ms"] for r in results], 99)),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()
    report = measure(args.url)
    Path("reports/evidence/deployed-cold.json").write_text(json.dumps(report, indent=2) + "\n")
    if args.enforce:
        targets = json.loads(Path("monitoring/slo.json").read_text())
        assert report["p95_ms"] <= targets["cold_p95_ms"], "Frozen cold p95 target exceeded"
        assert report["p99_ms"] <= targets["cold_p99_ms"], "Frozen cold p99 target exceeded"
