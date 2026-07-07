from paper_learning.core.dedupe import dedupe_papers
from paper_learning.core.models import Paper


def test_dedupe_uses_identifier_before_title() -> None:
    papers = [
        Paper(
            id="a",
            title="Same Paper",
            source="arxiv",
            topics=["llm_agent"],
            url="https://example.com/a",
            identifiers={"arxiv_id": "1234.5678"},
        ),
        Paper(
            id="b",
            title="Same Paper revised",
            source="semantic_scholar",
            topics=["llm_agent"],
            url="https://example.com/b",
            identifiers={"arxiv_id": "1234.5678"},
        ),
    ]

    assert dedupe_papers(papers) == [papers[0]]


def test_dedupe_falls_back_to_normalized_title() -> None:
    papers = [
        {"id": "a", "title": "A  Useful   Paper"},
        {"id": "b", "title": "a useful paper"},
    ]

    assert dedupe_papers(papers) == [papers[0]]
