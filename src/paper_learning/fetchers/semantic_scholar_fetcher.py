from __future__ import annotations


def fetch_semantic_scholar_candidates(*, query: str | None = None, limit: int = 20) -> list[dict]:
    """Return no primary candidates.

    Semantic Scholar is used as a v0.3 metadata enrichment source, not as a
    recommendation source. See paper_learning.enrichers.semantic_scholar.
    """

    return []
