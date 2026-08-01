import json
from datetime import datetime, timezone

from paper_learning.fetchers.biorxiv_fetcher import fetch_biorxiv_candidates
from paper_learning.core.dedupe import dedupe_papers
from paper_learning.core.normalize import normalize_papers


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


def _payload(doi: str, category: str = "neuroscience") -> dict:
    return {
        "collection": [
            {
                "doi": doi,
                "title": "Memory and learning in neural systems",
                "authors": "Ada Lovelace",
                "date": "2026-07-10",
                "category": category,
                "abstract": "Memory, cognition, and behavior.",
            }
        ]
    }


def test_biorxiv_keeps_biorxiv_when_medrxiv_fails(monkeypatch, caplog) -> None:
    def fake_fetch(*, server, interval, category):
        if server == "medrxiv":
            raise OSError("offline")
        return _payload("10.1101/good")

    monkeypatch.setattr("paper_learning.fetchers.biorxiv_fetcher._fetch_details_payload", fake_fetch)

    candidates = fetch_biorxiv_candidates(
        servers=["biorxiv", "medrxiv"],
        categories=["neuroscience"],
        now=datetime(2026, 7, 13, tzinfo=timezone.utc),
    )

    assert [paper.identifiers["doi"] for paper in candidates] == ["10.1101/good"]
    assert "server=medrxiv" in caplog.text
    assert "category=neuroscience" in caplog.text
    assert "interval=2026-07-06/2026-07-13" in caplog.text


def test_biorxiv_keeps_other_category_after_failure(monkeypatch) -> None:
    def fake_fetch(*, server, interval, category):
        if category == "animal behavior and cognition":
            raise ValueError("invalid payload")
        return _payload("10.1101/neuro")

    monkeypatch.setattr("paper_learning.fetchers.biorxiv_fetcher._fetch_details_payload", fake_fetch)

    candidates = fetch_biorxiv_candidates(
        servers=["biorxiv"],
        categories=["animal behavior and cognition", "neuroscience"],
    )

    assert [paper.identifiers["doi"] for paper in candidates] == ["10.1101/neuro"]


def test_biorxiv_all_requests_fail(monkeypatch) -> None:
    def fake_fetch(*, server, interval, category):
        raise json.JSONDecodeError("bad", "", 0)

    monkeypatch.setattr("paper_learning.fetchers.biorxiv_fetcher._fetch_details_payload", fake_fetch)

    assert fetch_biorxiv_candidates(
        servers=["biorxiv", "medrxiv"],
        categories=["neuroscience"],
    ) == []


def test_biorxiv_invalid_payload_does_not_stop_later_request(monkeypatch) -> None:
    def fake_fetch(*, server, interval, category):
        if server == "biorxiv":
            return {"collection": "invalid"}
        return _payload("10.1101/med")

    monkeypatch.setattr("paper_learning.fetchers.biorxiv_fetcher._fetch_details_payload", fake_fetch)

    candidates = fetch_biorxiv_candidates(
        servers=["biorxiv", "medrxiv"],
        categories=["neuroscience"],
    )

    assert [paper.identifiers["doi"] for paper in candidates] == ["10.1101/med"]


def test_same_doi_from_different_servers_is_deduped_downstream(monkeypatch) -> None:
    monkeypatch.setattr(
        "paper_learning.fetchers.biorxiv_fetcher._fetch_details_payload",
        lambda **_kwargs: _payload("10.1101/shared"),
    )

    candidates = fetch_biorxiv_candidates(
        servers=["biorxiv", "medrxiv"],
        categories=["neuroscience"],
    )

    assert len(candidates) == 2
    assert len(dedupe_papers(normalize_papers(candidates))) == 1


def test_biorxiv_filters_records_after_reference_date(monkeypatch) -> None:
    payload = _payload("10.1101/future")
    payload["collection"][0]["date"] = "2026-07-14"
    monkeypatch.setattr(
        "paper_learning.fetchers.biorxiv_fetcher._fetch_details_payload",
        lambda **_kwargs: payload,
    )

    candidates = fetch_biorxiv_candidates(
        categories=["neuroscience"],
        servers=["biorxiv"],
        now=datetime(2026, 7, 13, 22, 10, tzinfo=timezone.utc),
    )

    assert candidates == []
