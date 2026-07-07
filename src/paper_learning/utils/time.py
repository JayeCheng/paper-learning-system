from __future__ import annotations

from datetime import datetime, timezone


def utc_now_string() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today_string() -> str:
    return datetime.now(timezone.utc).date().isoformat()
