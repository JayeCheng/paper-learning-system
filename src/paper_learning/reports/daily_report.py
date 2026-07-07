from __future__ import annotations

from pathlib import Path

from paper_learning.core.models import DailyReport, Paper
from paper_learning.reports.json_renderer import render_daily_json
from paper_learning.reports.markdown_renderer import render_daily_markdown
from paper_learning.utils.time import today_string, utc_now_string


def build_daily_report(
    papers: list[Paper] | None = None,
    *,
    date: str | None = None,
    summary: str | None = None,
) -> DailyReport:
    report_date = date or today_string()
    paper_list = papers or []
    return DailyReport(
        date=report_date,
        generated_at=utc_now_string(),
        summary=summary or "v0.0 placeholder report. Fetching and ranking are not implemented yet.",
        papers=paper_list,
        s_level_candidate_ids=[],
        knowledge_graph_delta=[],
        next_actions=["Implement source fetchers", "Add real ranking inputs", "Publish public JSON"],
    )


def write_daily_report(
    report: DailyReport,
    *,
    markdown_path: Path | None = None,
    json_path: Path | None = None,
) -> tuple[Path, Path]:
    markdown_path = markdown_path or Path("daily") / f"{report.date}.md"
    json_path = json_path or Path("data/public") / f"daily-{report.date}.json"

    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    markdown_path.write_text(render_daily_markdown(report), encoding="utf-8")
    json_path.write_text(render_daily_json(report), encoding="utf-8")
    return markdown_path, json_path
