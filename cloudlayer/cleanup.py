"""Scheduled lifetime enforcement for capstone resources only."""

import os
from datetime import datetime, timezone
from cloudlayer.config import settings
from cloudlayer.teardown import EXPECTED, teardown

expiry = os.environ.get("TEARDOWN_AFTER")
if os.environ.get("MANUAL") == "true" or (
    expiry and datetime.now(timezone.utc) >= datetime.fromisoformat(expiry)
):
    teardown(settings(), EXPECTED)
else:
    print("Retention has not expired; no resources changed")
