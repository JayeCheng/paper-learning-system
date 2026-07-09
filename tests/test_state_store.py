from pathlib import Path
from tempfile import TemporaryDirectory

from paper_learning.core.models import Paper
from paper_learning.core.state_store import load_papers, papers_path, upsert_papers


def _paper(paper_id: str, title: str) -> Paper:
    return Paper(
        id=paper_id,
        title=title,
        source="arxiv",
        source_type="recent_24h",
        source_group="llm_agent",
        topics=["llm_agent"],
        categories=["cs.CL"],
        url=f"https://example.com/{paper_id}",
    )


def test_papers_jsonl_accumulates_across_daily_runs() -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)

        upsert_papers([_paper("p1", "First")], root=root)
        upsert_papers([_paper("p2", "Second")], root=root)

        papers = load_papers(root)
        lines = papers_path(root).read_text(encoding="utf-8").splitlines()

        assert [paper.id for paper in papers] == ["p1", "p2"]
        assert len(lines) == 2
