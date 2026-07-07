from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any


def _get(paper: Any, key: str, default: Any = None) -> Any:
    if isinstance(paper, dict):
        return paper.get(key, default)
    return getattr(paper, key, default)


def _fingerprint(paper: Any) -> str:
    identifiers = _get(paper, "identifiers", {}) or {}
    for key in ("doi", "arxiv_id", "arxiv", "semantic_scholar_id"):
        value = identifiers.get(key)
        if value:
            return f"{key}:{str(value).lower().strip()}"

    title = str(_get(paper, "title", "")).lower()
    title = re.sub(r"[^a-z0-9]+", " ", title).strip()
    return f"title:{title}"


def dedupe_papers(papers: Iterable[Any]) -> list[Any]:
    seen: set[str] = set()
    unique: list[Any] = []

    for paper in papers:
        key = _fingerprint(paper)
        if key in seen:
            continue
        seen.add(key)
        unique.append(paper)

    return unique
