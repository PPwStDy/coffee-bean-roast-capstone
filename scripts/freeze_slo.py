"""Create the first fixed targets from completed deployed benchmark evidence."""

import json
from pathlib import Path
from loadtest.bench import freeze

warm = json.loads(Path("reports/evidence/deployed-warm.json").read_text())
cold = json.loads(Path("reports/evidence/deployed-cold.json").read_text())
image = json.loads(Path("reports/evidence/container-image.json").read_text())
print(json.dumps(freeze(warm, cold, image["Size"]), indent=2))
