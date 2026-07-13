import json

from paper_learning.fetchers.openreview_fetcher import fetch_openreview_candidates


class _Response:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_openreview_fetcher_parses_mock_response(monkeypatch) -> None:
    payload = {
        "notes": [
            {
                "id": "abc123",
                "forum": "abc123",
                "cdate": 1770000000000,
                "content": {
                    "title": {"value": "A Strong Agent Paper"},
                    "abstract": {"value": "Agent benchmark with released code."},
                    "authors": {"value": ["Ada Lovelace", "Grace Hopper"]},
                    "venue": {"value": "ICLR 2026"},
                    "pdf": {"value": "/pdf?id=abc123"},
                },
            }
        ]
    }

    def fake_urlopen(request, timeout):
        assert "content.venueid=ICLR.cc%2F2026%2FConference" in request.full_url
        return _Response(payload)

    monkeypatch.setattr("paper_learning.fetchers.openreview_fetcher.urlopen", fake_urlopen)

    candidates = fetch_openreview_candidates(venue_ids=["ICLR.cc/2026/Conference"], limit=5)

    assert len(candidates) == 1
    assert candidates[0].id == "openreview:abc123"
    assert candidates[0].source == "openreview"
    assert candidates[0].venue == "ICLR 2026"
    assert candidates[0].pdf_url == "https://openreview.net/pdf?id=abc123"


def test_openreview_fetcher_degrades_to_empty_on_network_failure(monkeypatch, caplog) -> None:
    def fake_urlopen(_request, timeout):
        raise OSError("network down")

    monkeypatch.setattr("paper_learning.fetchers.openreview_fetcher.urlopen", fake_urlopen)

    assert fetch_openreview_candidates(venue_ids=["ICLR.cc/2026/Conference"]) == []
    assert "OpenReview fetch failed" in caplog.text
