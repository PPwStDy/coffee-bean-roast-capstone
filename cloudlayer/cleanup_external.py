"""Owner cleanup of precisely recorded capstone budget and external role grants."""

import json
from pathlib import Path

from cloudlayer.cli import az
from cloudlayer.teardown import GROUP

SUBSCRIPTION = "6638a4ea-96da-4326-969a-2e40305cfc83"
PRINCIPAL = "408b862a-b296-407a-98b8-96267f7a55ce"
EXPECTED_IDS = {
    "ci-cost-reader-role.json": "b241401b-6331-4c6c-a71b-7fa475e49879",
    "ci-ml-role.json": "2ae3f8c3-c8a1-41dc-8278-50b7f2fe46b6",
}


def cleanup():
    if az("group", "exists", "--name", GROUP):
        raise ValueError("Remove the owned group first; external access is needed until teardown")
    evidence = Path("reports/evidence")
    budget = json.loads((evidence / "budget-raw.json").read_text())
    if budget["name"] != "itcs355-6688218-capstone":
        raise ValueError("Unexpected budget ownership")
    dimension = budget.get("properties", {}).get("filter", {}).get("dimensions", {})
    if dimension != {"name": "ResourceGroupName", "operator": "In", "values": [GROUP]}:
        raise ValueError("Budget does not exclusively identify the capstone group")
    budget_id = f"/subscriptions/{SUBSCRIPTION}/providers/Microsoft.Consumption/budgets/{budget['name']}"
    az(
        "rest",
        "--method",
        "delete",
        "--url",
        f"https://management.azure.com{budget_id}?api-version=2024-08-01",
    )
    deleted = [budget_id]
    for filename, assignment in EXPECTED_IDS.items():
        record = json.loads((evidence / filename).read_text())
        if record["principalId"] != PRINCIPAL or record["id"].split("/")[-1] != assignment:
            raise ValueError("Recorded role does not belong to the capstone identity")
        az("role", "assignment", "delete", "--ids", record["id"])
        deleted.append(record["id"])
        remaining = az("role", "assignment", "list", "--scope", record["scope"], "--all")
        if any(r["id"] == record["id"] for r in remaining):
            raise RuntimeError("Owned role assignment still exists")
    remaining = az("consumption", "budget", "list")
    if any(b["name"] == budget["name"] for b in remaining):
        raise RuntimeError("Capstone budget still exists")
    result = {"deleted_ids": deleted, "verified_absent": True, "shared_roles_preserved": True}
    (evidence / "external-cleanup.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(cleanup(), indent=2))
