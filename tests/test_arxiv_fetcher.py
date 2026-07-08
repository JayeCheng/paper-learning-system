from datetime import datetime, timezone

from paper_learning.fetchers.arxiv_fetcher import _parse_arxiv_atom


def test_parse_arxiv_atom_returns_candidates_and_filters_by_cutoff() -> None:
    payload = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
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
    )

    assert len(candidates) == 1
    assert candidates[0].id == "arxiv:2601.00001v1"
    assert candidates[0].source_type == "recent_24h"
    assert candidates[0].categories == ["cs.CL"]
    assert candidates[0].pdf_url == "http://arxiv.org/pdf/2601.00001v1"
