"""Deploy zero-traffic candidate, validate it, then promote or restore previous traffic."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from cloudlayer.cli import az
from cloudlayer.budget import calculate
from scripts.endpoint_checks import check


def verify_traffic(group, endpoint, expected):
    """Wait for ARM to report the requested revision weights after an async update."""
    wanted = {t["revisionName"]: t["weight"] for t in expected if t.get("weight", 0)}
    deadline = time.monotonic() + 300
    while True:
        actual = az("containerapp", "show", "--name", endpoint, "--resource-group", group)
        traffic = actual["properties"]["configuration"]["ingress"]["traffic"]
        observed = {t.get("revisionName"): t["weight"] for t in traffic if t.get("weight", 0)}
        if observed == wanted:
            return traffic
        if time.monotonic() >= deadline:
            raise TimeoutError("Azure did not apply the requested revision traffic weights")
        time.sleep(5)


def deploy_candidate(config, digest, endpoint):
    calculate()
    group = config["PROJECT_ID"]
    metadata = json.loads(Path("reports/model_metadata.json").read_text())
    if metadata.get("evaluation_status") != "retrained_on_deduplicated_splits" or not metadata.get(
        "test_evaluation"
    ):
        raise ValueError(
            "Production release requires clean retraining and completed selected-export test evaluation"
        )
    apps = az("containerapp", "list", "--resource-group", group)
    current = next((app for app in apps if app["name"] == endpoint), None)
    previous = current["properties"]["configuration"]["ingress"].get("traffic", []) if current else []
    previous_revision = next((t.get("revisionName") for t in previous if t.get("weight", 0) > 0), "")
    if current and not previous_revision:
        previous_revision = current["properties"]["latestReadyRevisionName"]
    suffix = "r" + str(int(time.time()))
    parameters = [
        f"imageDigest={digest}",
        f"environmentId={config['CONTAINER_ENVIRONMENT_ID']}",
        f"identityId={config['IDENTITY_REF']}",
        f"registry={config['CONTAINER_REGISTRY']}",
        f"modelVersion={metadata['model_version']}",
        f"appName={endpoint}",
        f"revisionSuffix={suffix}",
        f"previousRevision={previous_revision}",
    ]
    az(
        "deployment",
        "group",
        "validate",
        "--resource-group",
        group,
        "--template-file",
        "infra/app.bicep",
        "--parameters",
        *parameters,
    )
    result = az(
        "deployment",
        "group",
        "create",
        "--name",
        "capstone-api",
        "--resource-group",
        group,
        "--template-file",
        "infra/app.bicep",
        "--parameters",
        *parameters,
    )
    outputs = result["properties"]["outputs"]
    revision = outputs["revision"]["value"]
    candidate = az(
        "containerapp",
        "revision",
        "show",
        "--name",
        endpoint,
        "--resource-group",
        group,
        "--revision",
        revision,
    )
    url = "https://" + candidate["properties"]["fqdn"]
    evidence = {
        "time": datetime.now(timezone.utc).isoformat(),
        "digest": digest,
        "candidate": revision,
        "previous_traffic": previous,
        "candidate_url": url,
    }
    try:
        evidence["checks"] = check(url, metadata["model_version"])
        if Path("monitoring/slo.json").exists():
            from loadtest.bench import benchmark, enforce

            report = benchmark(url, 1000, 2)
            enforce(report)
            evidence["benchmark"] = report
        az(
            "containerapp",
            "ingress",
            "traffic",
            "set",
            "--name",
            endpoint,
            "--resource-group",
            group,
            "--revision-weight",
            f"{revision}=100",
        )
        evidence["promoted_traffic"] = verify_traffic(
            group, endpoint, [{"revisionName": revision, "weight": 100}]
        )
        evidence["promoted"] = True
    except Exception as exc:
        evidence.update(promoted=False, error=str(exc))
        if previous_revision:
            az(
                "containerapp",
                "ingress",
                "traffic",
                "set",
                "--name",
                endpoint,
                "--resource-group",
                group,
                "--revision-weight",
                *[f"{t.get('revisionName', previous_revision)}={t['weight']}" for t in previous],
            )
            expected = previous or [{"revisionName": previous_revision, "weight": 100}]
            evidence["rollback_verified"] = verify_traffic(group, endpoint, expected)
        az(
            "containerapp",
            "revision",
            "deactivate",
            "--name",
            endpoint,
            "--resource-group",
            group,
            "--revision",
            revision,
        )
        rejected = az(
            "containerapp",
            "revision",
            "show",
            "--name",
            endpoint,
            "--resource-group",
            group,
            "--revision",
            revision,
        )
        evidence["rejected_candidate_inactive"] = not rejected["properties"].get("active", True)
        if not evidence["rejected_candidate_inactive"]:
            raise RuntimeError("Rejected candidate is still active") from exc
        raise
    finally:
        Path("reports/evidence/candidate-deployment.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return outputs["url"]["value"]
