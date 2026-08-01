import os
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from zoneinfo import ZoneInfo

from paper_learning.core.daily_pipeline import build_candidate_pool, run_daily_pipeline
from paper_learning.core.models import PaperCandidate


def _candidate(
    arxiv_id: str,
    *,
    source_type: str = "recent_24h",
    published_date: str = "2026-07-07",
) -> PaperCandidate:
    return PaperCandidate(
        id=f"arxiv:{arxiv_id}",
        title=f"Paper {arxiv_id}",
        authors=["Author"],
        abstract="Abstract",
        source="arxiv",
        source_url=f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
        published_date=published_date,
        categories=["cs.CL"],
        tags=["cs.CL"],
        source_type=source_type,
        identifiers={"arxiv_id": arxiv_id},
    )


def test_candidate_pool_adds_classics_after_recent_dedupe() -> None:
    recent = [
        _candidate("2601.00001v1"),
        _candidate("2601.00001v2"),
        _candidate("2601.00002v1"),
        _candidate("2601.00002v2"),
        _candidate("2601.00002v3"),
        _candidate("2601.00002v4"),
    ]
    with TemporaryDirectory() as temp_dir:
        curriculum = Path(temp_dir)
        (curriculum / "llm_agent_classics.yaml").write_text(
            "\n".join(
                [
                    "track: llm_agent",
                    "items:",
                    '  - title: "Classic One"',
                    "    status: candidate",
                    "    reason: Important classic.",
                    '  - title: "Classic Two"',
                    "    status: candidate",
                    "    reason: Important classic.",
                    '  - title: "Classic Three"',
                    "    status: candidate",
                    "    reason: Important classic.",
                    '  - title: "Classic Four"',
                    "    status: candidate",
                    "    reason: Important classic.",
                ]
            ),
            encoding="utf-8",
        )

        papers = build_candidate_pool(recent, max_daily=6, curriculum_dir=curriculum)

        assert len(papers) == 6
        assert any(paper.source_type == "classic" for paper in papers)


def test_daily_pipeline_uses_classic_fallback_when_recent_dedupes_short() -> None:
    recent = [_candidate("2601.00001v1") for _ in range(6)]
    cwd = Path.cwd()
    with TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        try:
            curriculum = Path("curriculum")
            curriculum.mkdir()
            (curriculum / "llm_agent_classics.yaml").write_text(
                "\n".join(
                    [
                        "track: llm_agent",
                        "items:",
                        '  - title: "Classic One"',
                        "    status: candidate",
                        "    reason: Important classic.",
                        '  - title: "Classic Two"',
                        "    status: candidate",
                        "    reason: Important classic.",
                        '  - title: "Classic Three"',
                        "    status: candidate",
                        "    reason: Important classic.",
                        '  - title: "Classic Four"',
                        "    status: candidate",
                        "    reason: Important classic.",
                        '  - title: "Classic Five"',
                        "    status: candidate",
                        "    reason: Important classic.",
                    ]
                ),
                encoding="utf-8",
            )

            with patch("paper_learning.core.daily_pipeline.fetch_arxiv_candidates", return_value=recent):
                report, _markdown_path, _json_path = run_daily_pipeline("2026-07-07")

            assert len(report.papers) == 6
            assert any(paper.source_type == "classic" for paper in report.papers)
            assert Path("data/state/papers.jsonl").exists()
            assert Path("data/state/reading_status.json").exists()
            assert Path("data/state/run_history.json").exists()
            assert Path("data/public/reading_status.json").exists()
            assert Path("data/public/curriculum_progress.json").exists()
            assert Path("data/exports/daily_papers.csv").exists()
        finally:
            os.chdir(cwd)


def test_historical_report_uses_scheduled_reference_time_and_excludes_future_papers(
    tmp_path,
) -> None:
    past = _candidate("2607.00001v1", published_date="2026-07-07")
    future = _candidate("2607.00002v1", published_date="2026-07-08")
    observed: dict[str, datetime] = {}

    def fetch_arxiv(_config, *, now):
        observed["arxiv"] = now
        return [past]

    def fetch_openreview(_config, *, now):
        observed["openreview"] = now
        return [future]

    def fetch_biorxiv(_config, *, now):
        observed["biorxiv"] = now
        return []

    with (
        patch(
            "paper_learning.core.daily_pipeline.fetch_recent_candidates_by_group",
            side_effect=fetch_arxiv,
        ),
        patch(
            "paper_learning.core.daily_pipeline.fetch_openreview_candidates_by_config",
            side_effect=fetch_openreview,
        ),
        patch(
            "paper_learning.core.daily_pipeline.fetch_biorxiv_candidates_by_config",
            side_effect=fetch_biorxiv,
        ),
    ):
        report, _markdown_path, _json_path = run_daily_pipeline(
            "2026-07-07",
            root=tmp_path,
        )

    expected = datetime(2026, 7, 7, 6, 10, tzinfo=ZoneInfo("Asia/Singapore"))
    assert observed == {
        "arxiv": expected,
        "openreview": expected,
        "biorxiv": expected,
    }
    assert past.id in {paper.id for paper in report.papers}
    assert future.id not in {paper.id for paper in report.papers}
    assert all(
        not paper.published_date or paper.published_date <= report.date
        for paper in report.papers
    )
