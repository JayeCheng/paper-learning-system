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


def test_dedupe_normalizes_arxiv_versions_and_doi() -> None:
    papers = [
        {"id": "a", "title": "First", "identifiers": {"arxiv_id": "2401.12345v2"}},
        {"id": "b", "title": "Second", "identifiers": {"arxiv_id": "2401.12345v3"}},
        {"id": "c", "title": "Third", "identifiers": {"doi": "10.1000/ABC"}},
        {"id": "d", "title": "Fourth", "identifiers": {"doi": "10.1000/abc"}},
    ]

    assert dedupe_papers(papers) == [papers[0], papers[2]]
