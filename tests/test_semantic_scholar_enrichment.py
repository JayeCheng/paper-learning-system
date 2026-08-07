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


def _paper(**overrides) -> Paper:
    values = {
        "id": "manual:paper",
        "title": "Reliable Methods for Learning Representations",
        "source": "manual",
        "topics": ["llm_agent"],
        "url": "https://example.com/original",
        "authors": ["Ada Lovelace"],
        "published_date": "2025-05-01",
        "venue": "Original Venue",
        "citation_count": 3,
        "external_ids": {"Original": "keep"},
    }
    values.update(overrides)
    return Paper(**values)


def test_semantic_scholar_doi_lookup_is_exact(monkeypatch) -> None:
    client = SemanticScholarClient()
    seen = []

    def fake_read(url):
        seen.append(url)
        return {"citationCount": 9}

    monkeypatch.setattr(client, "_read_json", fake_read)
    enriched = client.enrich_paper(_paper(identifiers={"doi": "10.1234/example"}))

    assert "/paper/DOI:10.1234" in seen[0]
    assert enriched.citation_count == 9


def test_semantic_scholar_title_exact_match(monkeypatch) -> None:
    client = SemanticScholarClient()
    monkeypatch.setattr(
        client,
        "_read_json",
        lambda _url: {
            "data": [
                {
                    "title": "Reliable methods for learning representations!",
                    "authors": [{"name": "Ada Lovelace"}],
                    "year": 2025,
                    "citationCount": 42,
                }
            ]
        },
    )

    assert client.enrich_paper(_paper()).citation_count == 42


def test_semantic_scholar_rejects_similar_title_with_wrong_author(monkeypatch, caplog) -> None:
    client = SemanticScholarClient()
    monkeypatch.setattr(
        client,
        "_read_json",
        lambda _url: {
            "data": [
                {
                    "title": "Reliable Methods for Learning Representation",
                    "authors": [{"name": "Different Person"}],
                    "year": 2025,
                    "citationCount": 999,
                    "venue": "Wrong Venue",
                    "externalIds": {"DOI": "10.9999/wrong"},
                }
            ]
        },
    )
    original = _paper()

    enriched = client.enrich_paper(original)

    assert enriched == original
    assert "author_mismatch" in caplog.text


def test_semantic_scholar_rejects_title_match_with_distant_year(monkeypatch, caplog) -> None:
    client = SemanticScholarClient()
    monkeypatch.setattr(
        client,
        "_read_json",
        lambda _url: {
            "data": [
                {
                    "title": "Reliable Methods for Learning Representations",
                    "authors": [{"name": "Ada Lovelace"}],
                    "year": 2018,
                    "citationCount": 999,
                }
            ]
        },
    )

    assert client.enrich_paper(_paper()).citation_count == 3
    assert "year_mismatch" in caplog.text


def test_semantic_scholar_rejects_first_unrelated_result(monkeypatch) -> None:
    client = SemanticScholarClient()
    monkeypatch.setattr(
        client,
        "_read_json",
        lambda _url: {
            "data": [
                {
                    "title": "An Entirely Different Research Topic",
                    "authors": [{"name": "Ada Lovelace"}],
                    "year": 2025,
                    "citationCount": 999,
                }
            ]
        },
    )

    assert client.enrich_paper(_paper()).citation_count == 3


def test_semantic_scholar_skips_broad_classic_title(monkeypatch) -> None:
    client = SemanticScholarClient()

    def unexpected_call(_url):
        raise AssertionError("broad classic title must not trigger title search")

    monkeypatch.setattr(client, "_read_json", unexpected_call)
    original = _paper(title="Learning to Learn", source_type="classic", authors=[])

    assert client.enrich_paper(original) == original
