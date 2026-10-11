"""Create the first fixed targets from completed deployed benchmark evidence."""

import json
from pathlib import Path
from loadtest.bench import freeze

if Path("monitoring/slo.json").exists():
    raise FileExistsError("Initial targets are already frozen; do not replace the baseline evidence")
warm = json.loads(Path("reports/evidence/deployed-warm.json").read_text())
cold = json.loads(Path("reports/evidence/deployed-cold.json").read_text())
image = json.loads(Path("reports/evidence/container-image.json").read_text())
workflow = json.loads(Path("reports/evidence/performance-ci.json").read_text())
warm["workflow_url"] = workflow["url"]
warm["source_commit"] = workflow["headSha"]
cold["deployed_digest"] = image["deployed_digest"]
cold["source_commit"] = image["source_commit"]
Path("reports/evidence/initial-warm.json").write_text(json.dumps(warm, indent=2) + "\n")
Path("reports/evidence/initial-cold.json").write_text(json.dumps(cold, indent=2) + "\n")
Path("reports/evidence/initial-container-image.json").write_text(json.dumps(image, indent=2) + "\n")
print(json.dumps(freeze(warm, cold, image["Size"]), indent=2))
