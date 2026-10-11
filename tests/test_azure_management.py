"""Exercise the regional ARM fallback without network or resource mutations."""

import json
import subprocess

import pytest
from cloudlayer import cli


@pytest.mark.parametrize(
    "args,suffix,collection",
    [
        (("list",), "/containerApps", True),
        (("show", "--name", "api"), "/containerApps/api", False),
        (("revision", "list", "--name", "api"), "/api/revisions", True),
        (("revision", "show", "--name", "api", "--revision", "rev"), "/api/revisions/rev", False),
        (("replica", "list", "--name", "api", "--revision", "rev"), "/api/revisions/rev/replicas", True),
    ],
)
def test_management_paths(monkeypatch, args, suffix, collection):
    calls = []
    monkeypatch.setattr(cli, "subscription", lambda: "sub")

    def fake(*arguments):
        calls.append(arguments)
        return {"value": [{"name": "result"}]} if collection else {"name": "result"}

    monkeypatch.setattr(cli, "az", fake)
    result = cli.container_rest(("containerapp", *args, "--resource-group", "group"))
    assert calls[0][4].endswith(suffix + "?api-version=2025-07-01")
    assert result == ([{"name": "result"}] if collection else {"name": "result"})


def test_unrelated_cli_errors_are_not_hidden(monkeypatch):
    monkeypatch.setattr(
        cli.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess([], 1, "", "quota exceeded")
    )
    with pytest.raises(RuntimeError, match="quota exceeded"):
        cli.az("containerapp", "list", "--resource-group", "group")


def test_traffic_patch_preserves_ingress(monkeypatch):
    app = {"properties": {"configuration": {"ingress": {"external": True, "targetPort": 8080}}}}
    monkeypatch.setattr(cli, "subscription", lambda: "sub")

    def fake(*arguments):
        if arguments[2] == "patch":
            body = json.loads(arguments[-1])
            assert body["properties"]["configuration"]["ingress"]["external"]
            assert body["properties"]["configuration"]["ingress"]["targetPort"] == 8080
            return None
        return app

    monkeypatch.setattr(cli, "az", fake)
    result = cli.container_rest(
        (
            "containerapp",
            "ingress",
            "traffic",
            "set",
            "--name",
            "api",
            "--resource-group",
            "group",
            "--revision-weight",
            "new=100",
        )
    )
    assert result["properties"]["configuration"]["ingress"]["traffic"] == [
        {"revisionName": "new", "weight": 100}
    ]
