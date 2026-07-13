import json

from paper_learning.core.models import Paper
from paper_learning.enrichers.semantic_scholar import SemanticScholarClient, enrich_papers


class _Response:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_no_semantic_scholar_api_key_still_runs(monkeypatch) -> None:
    monkeypatch.delenv("SEMANTIC_SCHOLAR_API_KEY", raising=False)

    def fake_urlopen(request, timeout):
        assert "X-api-key" not in request.headers
        return _Response({"data": [{"citationCount": 3, "externalIds": {"CorpusId": "123"}}]})

    monkeypatch.setattr("paper_learning.enrichers.semantic_scholar.urlopen", fake_urlopen)
    paper = Paper(id="p1", title="No Key Paper", source="arxiv", topics=["llm_agent"], url="https://example.com/p1")

    enriched = enrich_papers([paper], client=SemanticScholarClient.from_env())[0]

    assert enriched.citation_count == 3
    assert enriched.external_ids["CorpusId"] == "123"
    assert "semantic_scholar" in enriched.enrichment_sources
