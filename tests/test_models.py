from paper_learning.core.models import PaperCandidate
from paper_learning.core.normalize import normalize_paper


def test_source_and_source_type_are_separate_fields() -> None:
    candidate = PaperCandidate(
        id="arxiv:2601.00001",
        title="A Recent Paper",
        authors=[],
        abstract="Abstract",
        source="arxiv",
        source_url="https://arxiv.org/abs/2601.00001",
        pdf_url="https://arxiv.org/pdf/2601.00001",
        published_date="2026-07-07",
        categories=["cs.AI"],
        tags=["cs.AI"],
        source_type="recent_24h",
        identifiers={"arxiv_id": "2601.00001"},
    )

    paper = normalize_paper(candidate)

    assert paper.source == "arxiv"
    assert paper.source_type == "recent_24h"
