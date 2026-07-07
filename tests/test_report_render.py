import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from paper_learning.core.models import Paper
from paper_learning.reports.daily_report import build_daily_report, write_daily_report
from paper_learning.reports.json_renderer import render_daily_json
from paper_learning.reports.markdown_renderer import render_daily_markdown


def test_report_renderers_include_paper_metadata() -> None:
    paper = Paper(
        id="p1",
        title="A Good Paper",
        source="arxiv",
        source_type="recent_24h",
        topics=["gpu_graphics"],
        categories=["cs.GR"],
        url="https://example.com/p1",
        recommendation_level="A",
        score=0.82,
    )
    report = build_daily_report([paper], date="2026-07-07", summary="One useful paper.")

    markdown = render_daily_markdown(report)
    payload = json.loads(render_daily_json(report))

    assert "A Good Paper" in markdown
    assert payload["date"] == "2026-07-07"
    assert payload["papers"][0]["id"] == "p1"


def test_write_daily_report_outputs_stable_paths_and_public_json() -> None:
    cwd = Path.cwd()
    with TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        try:
            paper = Paper(
                id="p1",
                title="A Good Paper",
                source="arxiv",
                source_type="recent_24h",
                topics=["llm_agent"],
                categories=["cs.AI"],
                url="https://example.com/p1",
                recommendation_level="S",
                selected_for_s_level=True,
                score=0.9,
            )
            report = build_daily_report([paper], date="2026-07-07")

            markdown_path, json_path = write_daily_report(report)

            assert markdown_path == Path("daily") / "2026" / "07" / "2026-07-07.md"
            assert json_path == Path("daily") / "2026" / "07" / "2026-07-07.json"
            assert Path("data/public/latest.json").exists()
            assert Path("data/public/daily_index.json").exists()
            assert Path("data/public/papers_index.json").exists()
            assert Path("data/public/knowledge_graph.json").exists()
            assert Path("data/exports/papers.jsonl").exists()
            assert Path("data/exports/papers.csv").exists()
            assert Path("data/exports/reading_status.csv").exists()

            latest = json.loads(Path("data/public/latest.json").read_text(encoding="utf-8"))
            index = json.loads(Path("data/public/daily_index.json").read_text(encoding="utf-8"))
            assert latest["latest"]["json_path"] == "daily/2026/07/2026-07-07.json"
            assert index["reports"][0]["date"] == "2026-07-07"
        finally:
            os.chdir(cwd)
