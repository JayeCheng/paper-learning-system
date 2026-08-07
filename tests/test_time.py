from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from paper_learning.utils.time import local_today_string, report_reference_time


def test_local_today_string_uses_singapore_date_for_github_actions_time() -> None:
    now = datetime(2026, 7, 7, 22, 10, tzinfo=timezone.utc)

    assert local_today_string(now=now) == "2026-07-08"


def test_report_reference_time_uses_singapore_0610_schedule() -> None:
    assert report_reference_time("2026-07-07") == datetime(
        2026,
        7,
        7,
        6,
        10,
        tzinfo=ZoneInfo("Asia/Singapore"),
    )
