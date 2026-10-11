"""Package committed source with verifiable Git lineage for a managed training job."""

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
if subprocess.check_output(
    ["git", "status", "--porcelain", "--untracked-files=no"], cwd=root, text=True
).strip():
    raise RuntimeError("Commit changes before packaging training")
target = root / "tmp/training-source"
if target.exists():
    shutil.rmtree(target)
target.mkdir(parents=True)
files = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
hashes = {}
for filename in files:
    if not filename or filename.startswith(("tests/fixtures/", "reports/evidence/")):
        continue
    source = root / filename
    destination = target / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    hashes[filename] = hashlib.sha256(source.read_bytes()).hexdigest()
(target / "provenance/source_revision.json").write_text(
    json.dumps({"git_commit": commit, "sha256": hashes}, indent=2) + "\n"
)
print(target)
