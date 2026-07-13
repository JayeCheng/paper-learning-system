import json
from datetime import datetime, timezone

from paper_learning.fetchers.biorxiv_fetcher import fetch_biorxiv_candidates


class _Response:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_biorxiv_fetcher_parses_relevant_mock_response(monkeypatch) -> None:
    payload = {
        "collection": [
            {
                "doi": "10.1101/2026.07.01.123456",
                "title": "Memory-guided decision making in neural circuits",
                "authors": "Ada Lovelace; Grace Hopper",
                "date": "2026-07-10",
                "category": "neuroscience",
                "abstract": "A cognitive neuroscience study of memory and behavior.",
            },
            {
                "doi": "10.1101/2026.07.01.999999",
                "title": "A broad cell biology screen",
                "authors": "Unrelated Author",
                "date": "2026-07-10",
                "category": "cell biology",
                "abstract": "A protein assay for cellular transport.",
            },
        ]
    }

    def fake_urlopen(request, timeout):
        assert "category=neuroscience" in request.full_url
        return _Response(payload)

    monkeypatch.setattr("paper_learning.fetchers.biorxiv_fetcher.urlopen", fake_urlopen)

    candidates = fetch_biorxiv_candidates(
        categories=["neuroscience"],
        servers=["biorxiv"],
        now=datetime(2026, 7, 13, tzinfo=timezone.utc),
        limit=10,
    )

    assert len(candidates) == 1
    assert candidates[0].source == "biorxiv"
    assert candidates[0].source_group == "cognition_social"
    assert candidates[0].authors == ["Ada Lovelace", "Grace Hopper"]
    assert candidates[0].external_ids == {"DOI": "10.1101/2026.07.01.123456"}


def test_biorxiv_fetcher_degrades_to_empty_on_network_failure(monkeypatch, caplog) -> None:
    def fake_urlopen(_request, timeout):
        raise OSError("network down")

    monkeypatch.setattr("paper_learning.fetchers.biorxiv_fetcher.urlopen", fake_urlopen)

    assert fetch_biorxiv_candidates(categories=["neuroscience"], servers=["biorxiv"]) == []
    assert "bioRxiv/medRxiv fetch failed" in caplog.text
