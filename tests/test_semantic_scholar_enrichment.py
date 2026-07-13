import json

from paper_learning.core.models import Paper
from paper_learning.enrichers.semantic_scholar import SemanticScholarClient


class _Response:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_semantic_scholar_enrichment_merges_metadata(monkeypatch) -> None:
    payload = {
        "authors": [{"name": "Ada Lovelace"}],
        "venue": "ICLR",
        "citationCount": 42,
        "influentialCitationCount": 7,
        "fieldsOfStudy": ["Computer Science"],
        "externalIds": {"DOI": "10.5555/example", "ArXiv": "2601.00001"},
        "openAccessPdf": {"url": "https://example.com/paper.pdf"},
    }

    def fake_urlopen(request, timeout):
        assert "ARXIV:2601.00001" in request.full_url
        assert request.headers["X-api-key"] == "secret"
        return _Response(payload)

    monkeypatch.setattr("paper_learning.enrichers.semantic_scholar.urlopen", fake_urlopen)
    paper = Paper(
        id="arxiv:2601.00001",
        title="A Paper",
        source="arxiv",
        topics=["llm_agent"],
        url="https://arxiv.org/abs/2601.00001",
        identifiers={"arxiv_id": "2601.00001"},
    )

    enriched = SemanticScholarClient(api_key="secret").enrich_paper(paper)

    assert enriched.citation_count == 42
    assert enriched.influential_citation_count == 7
    assert enriched.venue == "ICLR"
    assert enriched.fields_of_study == ["Computer Science"]
    assert enriched.external_ids["DOI"] == "10.5555/example"
    assert enriched.open_access_pdf_url == "https://example.com/paper.pdf"
    assert "semantic_scholar" in enriched.enrichment_sources
