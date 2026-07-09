import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from paper_learning.core.models import Paper
from paper_learning.core.state_store import ensure_reading_status_entries, load_papers, load_reading_statuses, upsert_papers
from paper_learning.reports.exports import write_exports


def _paper(paper_id: str, group: str) -> Paper:
    return Paper(
        id=paper_id,
        title=f"Paper {paper_id}",
        source="arxiv",
        source_type="recent_24h",
        source_group=group,
        topics=[group],
        categories=["cs.CL"],
        url=f"https://example.com/{paper_id}",
    )


def test_exports_use_full_state_and_daily_subset() -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        old_paper = _paper("old", "gpu_graphics")
        today_paper = _paper("today", "llm_agent")
        upsert_papers([old_paper], root=root)
        upsert_papers([today_paper], root=root)
        ensure_reading_status_entries(load_papers(root), root=root, updated_at="2026-07-09T00:00:00+00:00")

        write_exports(
            papers=load_papers(root),
            reading_statuses=load_reading_statuses(root),
            daily_papers=[today_paper],
            exports_dir=root / "data" / "exports",
        )

        jsonl_rows = [
            json.loads(line)
            for line in (root / "data/exports/papers.jsonl").read_text(encoding="utf-8").splitlines()
            if line
        ]
        with (root / "data/exports/daily_papers.csv").open(encoding="utf-8", newline="") as handle:
            daily_rows = list(csv.DictReader(handle))

        assert {row["id"] for row in jsonl_rows} == {"old", "today"}
        assert [row["id"] for row in daily_rows] == ["today"]
