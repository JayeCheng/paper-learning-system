from __future__ import annotations

import re

from paper_learning.core.models import Paper


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_paper(raw: dict) -> Paper:
    title = normalize_text(str(raw.get("title", "")))
    source = str(raw.get("source", "manual"))
    paper_id = str(raw.get("id") or raw.get("url") or title.lower())
    topics = list(raw.get("topics") or ["uncategorized"])

    return Paper(
        id=paper_id,
        title=title,
        source=source,
        topics=topics,
        url=str(raw.get("url", "")),
        authors=list(raw.get("authors") or []),
        abstract=normalize_text(str(raw.get("abstract", ""))),
        pdf_url=raw.get("pdf_url"),
        published_at=raw.get("published_at"),
        identifiers=dict(raw.get("identifiers") or {}),
        scores=dict(raw.get("scores") or {}),
        reading_status=str(raw.get("reading_status", "backlog")),
    )
