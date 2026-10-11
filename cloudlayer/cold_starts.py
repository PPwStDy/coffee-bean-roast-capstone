"""Measure real scale-to-zero cold starts; no probe may wake the app between trials."""

import argparse
import json
import time
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
    results = []
    for index in range(trials):
        # This waits for natural HTTP cooldown; management-plane queries do not wake serving replicas.
        deadline = time.monotonic() + 1800
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
        assert response.headers["x-model-version"] == response.json()["model_version"]
        results.append(
            {
                "trial": index + 1,
                "replicas_before_request": 0,
                "status": response.status_code,
                "latency_ms": elapsed,
                "model_version": response.json()["model_version"],
            }
        )
        Path("reports/evidence/cold-start-progress.json").write_text(json.dumps(results, indent=2) + "\n")
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
    args = parser.parse_args()
    Path("reports/evidence/deployed-cold.json").write_text(json.dumps(measure(args.url), indent=2) + "\n")
