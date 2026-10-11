"""Checked Azure CLI runner. Argument arrays avoid shell interpolation."""

import json
import subprocess
from functools import lru_cache
from urllib.parse import quote


def az(*args, parse=True):
    result = subprocess.run(
        ["az", *map(str, args), "--only-show-errors", "-o", "json"],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        if args[0] == "containerapp" and "is not registered" in result.stderr:
            # East Asia may be available while registration in other regions is pending.
            # ARM still validates registration/permissions; this bypasses only the CLI's global precheck.
            return container_rest(args)
        raise RuntimeError(result.stderr.strip())
    return json.loads(result.stdout) if parse and result.stdout.strip() else result.stdout.strip()


@lru_cache(maxsize=1)
def subscription():
    return az("account", "show")["id"]


def container_rest(args):
    def flag(name):
        return str(args[args.index(name) + 1])

    base = (
        f"https://management.azure.com/subscriptions/{subscription()}/resourceGroups/"
        f"{quote(flag('--resource-group'), safe='')}/providers/Microsoft.App/containerApps"
    )
    api = "?api-version=2025-07-01"
    if args[1] == "list":
        path = base
    else:
        path = base + "/" + quote(flag("--name"), safe="")
    if args[1] == "show":
        return az("rest", "--method", "get", "--url", path + api)
    if args[1] == "revision":
        path += "/revisions"
        if args[2] != "list":
            path += "/" + quote(flag("--revision"), safe="")
        if args[2] in {"activate", "deactivate", "restart"}:
            return az("rest", "--method", "post", "--url", path + "/" + args[2] + api)
        if args[2] == "show":
            return az("rest", "--method", "get", "--url", path + api)
    elif args[1:3] == ("replica", "list"):
        path += "/revisions/" + quote(flag("--revision"), safe="") + "/replicas"
    elif args[1:4] == ("ingress", "traffic", "set"):
        app = az("rest", "--method", "get", "--url", path + api)
        configuration = app["properties"]["configuration"]
        values = args[args.index("--revision-weight") + 1 :]
        traffic = [{"revisionName": v.rsplit("=", 1)[0], "weight": int(v.rsplit("=", 1)[1])} for v in values]
        if sum(t["weight"] for t in traffic) != 100:
            raise ValueError("Traffic weights must total100")
        configuration["ingress"]["traffic"] = traffic
        az(
            "rest",
            "--method",
            "patch",
            "--url",
            path + api,
            "--body",
            json.dumps({"properties": {"configuration": configuration}}),
        )
        return az("rest", "--method", "get", "--url", path + api)
    elif args[1] != "list":
        raise ValueError("Unsupported Container Apps management operation")
    items = []
    next_url = path + api
    while next_url:
        result = az("rest", "--method", "get", "--url", next_url)
        items.extend(result["value"])
        next_url = result.get("nextLink")
    return items
