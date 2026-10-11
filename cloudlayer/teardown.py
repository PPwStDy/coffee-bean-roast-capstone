"""Delete only the dedicated tagged capstone group; retain all shared lab resources."""

import json
from datetime import datetime, timezone
from pathlib import Path

from cloudlayer.cli import az

EXPECTED = {"course": "itcs355", "student": "6688218", "lab": "capstone"}
GROUP = "rg-itcs355-6688218-capstone"


def teardown(config, tags):
    if tags != EXPECTED or config["PROJECT_ID"] != GROUP:
        raise ValueError("Teardown accepts only the approved capstone group and exact ownership tags")
    if not az("group", "exists", "--name", GROUP):
        return []
    group = az("group", "show", "--name", GROUP)
    if any(group.get("tags", {}).get(k) != v for k, v in EXPECTED.items()):
        raise ValueError("Resource group ownership tags do not match")
    resources = az("resource", "list", "--resource-group", GROUP)
    if any(any(r.get("tags", {}).get(k) != v for k, v in EXPECTED.items()) for r in resources):
        raise ValueError("An unowned resource exists inside the group; refusing group deletion")
    shared = az(
        "ml",
        "workspace",
        "show",
        "--name",
        config["AZURE_ML_WORKSPACE"],
        "--resource-group",
        config["AZURE_ML_RESOURCE_GROUP"],
    )
    ids = [r["id"] for r in resources]
    az("group", "delete", "--name", GROUP, "--yes")
    if az("group", "exists", "--name", GROUP):
        raise RuntimeError("Group still exists after deletion")
    after = az(
        "ml",
        "workspace",
        "show",
        "--name",
        config["AZURE_ML_WORKSPACE"],
        "--resource-group",
        config["AZURE_ML_RESOURCE_GROUP"],
    )
    if after["id"] != shared["id"]:
        raise RuntimeError("Shared workspace preservation could not be verified")
    Path("reports/evidence/teardown.json").write_text(
        json.dumps(
            {
                "time": datetime.now(timezone.utc).isoformat(),
                "deleted_resources": ids,
                "group_absent": True,
                "shared_workspace_preserved": after["id"],
            },
            indent=2,
        )
        + "\n"
    )
    return ids


if __name__ == "__main__":
    from cloudlayer.config import settings

    teardown(settings(), EXPECTED)
