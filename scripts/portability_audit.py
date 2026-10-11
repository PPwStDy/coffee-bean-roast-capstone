"""Fail the build if cloud provider-specific strings leak into Layer 1 (src/, service/, tests/).

Enforces the ITCS355 Three-Layer Portability Contract.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCANNED = ["src", "service", "monitoring", "tests"]

FORBIDDEN = [
    (r"s3://", "S3 URI"),
    (r"gs://", "GCS URI"),
    (r"abfss://", "ADLS URI"),
    (r"amazonaws\.com", "AWS hostname"),
    (r"blob\.core\.windows\.net", "Azure hostname"),
    (r"googleapis\.com", "GCP hostname"),
    (r"azurecr\.io", "ACR hostname"),
    (r"dkr\.ecr\.", "ECR hostname"),
    (r"pkg\.dev", "Artifact Registry hostname"),
    (r"\bimport boto3\b", "AWS SDK"),
    (r"\bfrom azure\b", "Azure SDK"),
    (r"\bfrom google\.cloud\b", "GCP SDK"),
]


def main() -> int:
    hits: list[str] = []
    for folder in SCANNED:
        folder_path = ROOT / folder
        if not folder_path.exists():
            continue
        for path in folder_path.rglob("*.py"):
            for lineno, line in enumerate(path.read_text().splitlines(), 1):
                if line.lstrip().startswith("#"):
                    continue
                for pattern, label in FORBIDDEN:
                    if re.search(pattern, line, flags=re.MULTILINE):
                        rel = path.relative_to(ROOT)
                        hits.append(f"{rel}:{lineno}  {label}  ->  {line.strip()[:80]}")

    if hits:
        print("PORTABILITY AUDIT FAILED — provider details leaked outside cloudlayer/\n")
        for h in hits:
            print("  " + h)
        print("\nMove each reference into cloudlayer/ or into cloud.env.")
        return 1

    print(f"PORTABILITY AUDIT PASSED — {', '.join(SCANNED)} contain no provider-specific strings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
