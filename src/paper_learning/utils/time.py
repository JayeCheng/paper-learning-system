from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

DEFAULT_TIMEZONE_NAME = "Asia/Singapore"


def utc_now_string() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def local_today_string(
    timezone_name: str = DEFAULT_TIMEZONE_NAME,
    now: datetime | None = None,
) -> str:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(ZoneInfo(timezone_name)).date().isoformat()


def today_string() -> str:
    return local_today_string()
