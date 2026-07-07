from __future__ import annotations

import json

from paper_learning.core.models import DailyReport


def render_daily_json(report: DailyReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"
