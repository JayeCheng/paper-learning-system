import json

from paper_learning.core.models import Paper
from paper_learning.reports.daily_report import build_daily_report
from paper_learning.reports.json_renderer import render_daily_json
from paper_learning.reports.markdown_renderer import render_daily_markdown


def test_report_renderers_include_paper_metadata() -> None:
    paper = Paper(
        id="p1",
        title="A Good Paper",
        source="arxiv",
        topics=["gpu_graphics"],
        url="https://example.com/p1",
    )
    report = build_daily_report([paper], date="2026-07-07", summary="One useful paper.")

    markdown = render_daily_markdown(report)
    payload = json.loads(render_daily_json(report))

    assert "A Good Paper" in markdown
    assert payload["date"] == "2026-07-07"
    assert payload["papers"][0]["id"] == "p1"
