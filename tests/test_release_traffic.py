"""Traffic promotion must be verified against actual Azure revision weights."""

import pytest
from cloudlayer import release


def test_traffic_waits_for_actual_weights(monkeypatch):
    values = iter(
        [
            [{"revisionName": "old", "weight": 100}],
            [{"revisionName": "new", "weight": 100}, {"revisionName": "old", "weight": 0}],
        ]
    )
    monkeypatch.setattr(
        release, "az", lambda *args: {"properties": {"configuration": {"ingress": {"traffic": next(values)}}}}
    )
    monkeypatch.setattr(release.time, "sleep", lambda _: None)
    result = release.verify_traffic("group", "api", [{"revisionName": "new", "weight": 100}])
    assert result[0] == {"revisionName": "new", "weight": 100}


def test_traffic_timeout_is_not_success(monkeypatch):
    ticks = iter([0, 301])
    monkeypatch.setattr(release.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(
        release,
        "az",
        lambda *args: {
            "properties": {
                "configuration": {"ingress": {"traffic": [{"revisionName": "old", "weight": 100}]}}
            }
        },
    )
    with pytest.raises(TimeoutError, match="did not apply"):
        release.verify_traffic("group", "api", [{"revisionName": "new", "weight": 100}])
