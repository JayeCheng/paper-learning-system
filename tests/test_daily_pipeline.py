import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from paper_learning.core.daily_pipeline import build_candidate_pool, run_daily_pipeline
from paper_learning.core.models import PaperCandidate


def _candidate(arxiv_id: str, *, source_type: str = "recent_24h") -> PaperCandidate:
    return PaperCandidate(
        id=f"arxiv:{arxiv_id}",
        title=f"Paper {arxiv_id}",
        authors=["Author"],
        abstract="Abstract",
        source="arxiv",
        source_url=f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
        published_date="2026-07-07",
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
        finally:
            os.chdir(cwd)
