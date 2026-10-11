"""Release entry point: refreshed budget, Linux image, immutable digest and safe promotion."""

import json
from pathlib import Path
import subprocess
from datetime import datetime, timezone
from cloudlayer.adapter import AzureCloudAdapter
from cloudlayer.budget import calculate
from cloudlayer.cli import az
from cloudlayer.config import settings

config = settings()
# Read current spend on every deployment; earlier evidence is not a credit balance.
now = datetime.now(timezone.utc)
query = {
    "type": "ActualCost",
    "timeframe": "Custom",
    "timePeriod": {"from": f"{now.year}-01-01T00:00:00Z", "to": now.strftime("%Y-%m-%dT%H:%M:%SZ")},
    "dataset": {
        "granularity": "None",
        "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
        "grouping": [{"type": "Dimension", "name": "ResourceGroupName"}],
    },
}
result = az(
    "rest",
    "--method",
    "post",
    "--url",
    f"https://management.azure.com/subscriptions/{config['AZURE_SUBSCRIPTION_ID']}/providers/Microsoft.CostManagement/query?api-version=2023-11-01",
    "--body",
    json.dumps(query),
)
Path("reports/evidence/azure-course-spending.json").write_text(json.dumps(result, indent=2) + "\n")
calculate()
commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
local_tag = "coffee-roast:" + commit[:12]
subprocess.run(["docker", "build", "--platform", "linux/amd64", "-t", local_tag, "."], check=True)
image = json.loads(subprocess.check_output(["docker", "image", "inspect", local_tag], text=True))[0]
Path("reports/evidence/container-image.json").write_text(
    json.dumps(
        {
            "Id": image["Id"],
            "Size": image["Size"],
            "Architecture": image["Architecture"],
            "Os": image["Os"],
            "source_commit": commit,
        },
        indent=2,
    )
    + "\n"
)
adapter = AzureCloudAdapter(config)
digest = adapter.push_image(local_tag)
Path("reports/evidence/image-digest.json").write_text(
    json.dumps({"digest": digest, "source_commit": commit}, indent=2) + "\n"
)
print(adapter.deploy(digest, config["ENDPOINT_NAME"], "2cpu-4Gi"))
