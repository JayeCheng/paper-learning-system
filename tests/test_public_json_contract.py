import json
from pathlib import Path
from tempfile import TemporaryDirectory

from paper_learning.core.models import Paper
from paper_learning.core.state_store import ensure_reading_status_entries, upsert_papers
from paper_learning.reports.daily_report import build_daily_report, with_generated_paths
from paper_learning.reports.public_json import write_public_json


def _paper() -> Paper:
    return Paper(
        id="p1",
        title="Public Paper",
        source="arxiv",
        source_type="recent_24h",
        source_group="llm_agent",
        topics=["llm_agent"],
        categories=["cs.CL"],
        url="https://example.com/p1",
        selected_for_s_level=True,
        recommendation_level="S",
        score=0.9,
    )


def test_public_json_files_are_generated_from_state_contract() -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        paper = _paper()
        all_papers = upsert_papers([paper], root=root)
        statuses = ensure_reading_status_entries([paper], root=root, updated_at="2026-07-09T00:00:00+00:00")
        report = build_daily_report([paper], date="2026-07-09")
        report = with_generated_paths(
            report,
            markdown_path=root / "daily/2026/07/2026-07-09.md",
            json_path=root / "daily/2026/07/2026-07-09.json",
            public_dir=root / "data/public",
            exports_dir=root / "data/exports",
            state_dir=root / "data/state",
            root=root,
        )
        run_history = [
            {
                "date": report.date,
                "generated_at": report.generated_at,
                "generated_paths": report.generated_paths,
                "paper_count": len(report.papers),
                "s_level_paper_id": report.s_level_paper_id,
                "status": "success",
            }
        ]

        write_public_json(
            report=report,
            papers=all_papers,
            reading_statuses=statuses,
            run_history=run_history,
            public_dir=root / "data/public",
        )

        for name in [
            "latest.json",
            "daily_index.json",
            "papers_index.json",
            "knowledge_graph.json",
            "reading_status.json",
            "curriculum_progress.json",
        ]:
            assert (root / "data/public" / name).exists()

        reading_status = json.loads((root / "data/public/reading_status.json").read_text(encoding="utf-8"))
        curriculum = json.loads((root / "data/public/curriculum_progress.json").read_text(encoding="utf-8"))

        assert reading_status["statuses"][0]["paper_id"] == "p1"
        assert curriculum["tracks"][0]["next_paper_ids"] == ["p1"]


def test_public_json_files_have_matching_schemas() -> None:
    expected = {
        "latest.schema.json",
        "daily_index.schema.json",
        "papers_index.schema.json",
        "knowledge_graph.schema.json",
        "reading_status.schema.json",
        "curriculum_progress.schema.json",
    }

    assert expected <= {path.name for path in Path("schemas").glob("*.schema.json")}
