"""Checked Azure CLI runner. Argument arrays avoid shell interpolation."""
import json
import subprocess


def az(*args, parse=True):
    result = subprocess.run(["az", *map(str, args), "--only-show-errors", "-o", "json"],
                            check=True, capture_output=True, text=True)
    return json.loads(result.stdout) if parse and result.stdout.strip() else result.stdout.strip()
