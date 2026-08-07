import json
from datetime import datetime, timezone

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
    assert candidates[0].source_type == "conference_review"
    assert candidates[0].venue == "ICLR 2026"
    assert candidates[0].pdf_url == "https://openreview.net/pdf?id=abc123"


def test_openreview_fetcher_degrades_to_empty_on_network_failure(monkeypatch, caplog) -> None:
    def fake_urlopen(_request, timeout):
        raise OSError("network down")

    monkeypatch.setattr("paper_learning.fetchers.openreview_fetcher.urlopen", fake_urlopen)

    assert fetch_openreview_candidates(venue_ids=["ICLR.cc/2026/Conference"]) == []
    assert "OpenReview fetch failed" in caplog.text


def _note(note_id: str) -> dict:
    return {
        "id": note_id,
        "content": {
            "title": {"value": f"Paper {note_id}"},
            "authors": {"value": ["Author"]},
            "year": {"value": 2026},
        },
    }


def test_openreview_keeps_success_before_later_failure(monkeypatch, caplog) -> None:
    def fake_fetch(*, venue_id, limit):
        if venue_id == "bad":
            raise OSError("network down")
        return {"notes": [_note(venue_id)]}

    monkeypatch.setattr("paper_learning.fetchers.openreview_fetcher._fetch_notes_payload", fake_fetch)

    candidates = fetch_openreview_candidates(venue_ids=["good", "bad"])

    assert [paper.id for paper in candidates] == ["openreview:good"]
    assert "venue_id=bad" in caplog.text


def test_openreview_keeps_success_after_earlier_failure(monkeypatch) -> None:
    def fake_fetch(*, venue_id, limit):
        if venue_id == "bad":
            raise json.JSONDecodeError("bad json", "", 0)
        return {"notes": [_note(venue_id)]}

    monkeypatch.setattr("paper_learning.fetchers.openreview_fetcher._fetch_notes_payload", fake_fetch)

    assert [paper.id for paper in fetch_openreview_candidates(venue_ids=["bad", "good"])] == [
        "openreview:good"
    ]


def test_openreview_all_venues_fail(monkeypatch) -> None:
    def fake_fetch(*, venue_id, limit):
        raise OSError(venue_id)

    monkeypatch.setattr("paper_learning.fetchers.openreview_fetcher._fetch_notes_payload", fake_fetch)

    assert fetch_openreview_candidates(venue_ids=["bad-1", "bad-2"]) == []


def test_openreview_invalid_payload_isolated_per_venue(monkeypatch, caplog) -> None:
    def fake_fetch(*, venue_id, limit):
        if venue_id == "malformed":
            return {"notes": "not-a-list"}
        return {"notes": [_note(venue_id)]}

    monkeypatch.setattr("paper_learning.fetchers.openreview_fetcher._fetch_notes_payload", fake_fetch)

    candidates = fetch_openreview_candidates(venue_ids=["malformed", "good"])

    assert [paper.id for paper in candidates] == ["openreview:good"]
    assert "venue_id=malformed" in caplog.text


def test_openreview_filters_submissions_after_reference_date(monkeypatch) -> None:
    future = _note("future")
    future["cdate"] = int(
        datetime(2026, 8, 2, tzinfo=timezone.utc).timestamp() * 1000
    )
    monkeypatch.setattr(
        "paper_learning.fetchers.openreview_fetcher._fetch_notes_payload",
        lambda **_kwargs: {"notes": [future]},
    )

    candidates = fetch_openreview_candidates(
        venue_ids=["ICLR.cc/2026/Conference"],
        now=datetime(2026, 8, 1, 22, 10, tzinfo=timezone.utc),
    )

    assert candidates == []
