from __future__ import annotations

import re
import hashlib
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
            normalized = str(value).lower().strip().removeprefix("arxiv:")
            normalized = re.sub(r"v\d+$", "", normalized)
            return f"{key}:{normalized}"

    title = str(_get(paper, "title", "")).lower()
    title = re.sub(r"[^a-z0-9]+", " ", title).strip()
    title_hash = hashlib.sha1(title.encode("utf-8")).hexdigest()[:16]
    return f"title_hash:{title_hash}"


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
