from datetime import datetime, timezone

from paper_learning.utils.time import local_today_string


def test_local_today_string_uses_singapore_date_for_github_actions_time() -> None:
    now = datetime(2026, 7, 7, 22, 10, tzinfo=timezone.utc)

    assert local_today_string(now=now) == "2026-07-08"
