from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

from paper_learning.fetchers.arxiv_fetcher import (
    _parse_arxiv_atom,
    fetch_arxiv_candidates,
)


def test_parse_arxiv_atom_returns_candidates_and_filters_by_cutoff() -> None:
    payload = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2601.99999v1</id>
    <published>2026-07-08T00:00:00Z</published>
    <title> Future Paper </title>
    <summary> This paper is after the reference time. </summary>
    <author><name>Future Author</name></author>
    <category term="cs.CL" />
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2601.00001v1</id>
    <published>2026-07-07T22:10:00Z</published>
    <title> A Useful Paper </title>
    <summary> A useful abstract. </summary>
    <author><name>Ada Lovelace</name></author>
    <category term="cs.CL" />
    <link href="http://arxiv.org/pdf/2601.00001v1" title="pdf" type="application/pdf" />
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2501.00001v1</id>
    <published>2025-01-01T00:00:00Z</published>
    <title> Old Paper </title>
    <summary> Old abstract. </summary>
    <author><name>Grace Hopper</name></author>
    <category term="cs.AR" />
  </entry>
</feed>
"""

    candidates = _parse_arxiv_atom(
        payload,
        source_type="recent_24h",
        cutoff=datetime(2026, 7, 7, 0, 0, tzinfo=timezone.utc),
        reference_time=datetime(2026, 7, 7, 22, 10, tzinfo=timezone.utc),
    )

    assert len(candidates) == 1
    assert candidates[0].id == "arxiv:2601.00001v1"
    assert candidates[0].source_type == "recent_24h"
    assert candidates[0].categories == ["cs.CL"]
    assert candidates[0].pdf_url == "http://arxiv.org/pdf/2601.00001v1"


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self) -> bytes:
        return b'<feed xmlns="http://www.w3.org/2005/Atom"></feed>'


def test_fetch_arxiv_queries_the_historical_reference_window(monkeypatch) -> None:
    captured = {}

    def fake_urlopen(request, timeout):
        captured["query"] = parse_qs(urlparse(request.full_url).query)["search_query"][0]
        return _Response()

    monkeypatch.setattr("paper_learning.fetchers.arxiv_fetcher.urlopen", fake_urlopen)

    candidates = fetch_arxiv_candidates(
        categories=["cs.AI"],
        window_days=7,
        now=datetime(2026, 7, 7, 6, 10, tzinfo=ZoneInfo("Asia/Singapore")),
    )

    assert candidates == []
    assert captured["query"] == (
        "(cat:cs.AI) AND submittedDate:[202606292210 TO 202607062210]"
    )
