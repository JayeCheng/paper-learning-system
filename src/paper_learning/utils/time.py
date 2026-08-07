from __future__ import annotations

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

DEFAULT_TIMEZONE_NAME = "Asia/Singapore"
DEFAULT_REPORT_TIME = time(hour=6, minute=10)


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


def report_reference_time(
    report_date: str,
    *,
    timezone_name: str = DEFAULT_TIMEZONE_NAME,
) -> datetime:
    """Return the timezone-aware scheduled reference time for a report date."""

    return datetime.combine(
        date.fromisoformat(report_date),
        DEFAULT_REPORT_TIME,
        tzinfo=ZoneInfo(timezone_name),
    )
