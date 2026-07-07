from __future__ import annotations

from dataclasses import asdict, is_dataclass
import re

from paper_learning.core.models import Paper, PaperCandidate

CATEGORY_TOPIC_MAP = {
    "cs.GR": "gpu_graphics",
    "cs.CV": "gpu_graphics",
    "cs.AR": "architecture",
    "cs.DC": "architecture",
    "cs.PF": "architecture",
    "cs.AI": "llm_agent",
    "cs.CL": "llm_agent",
    "cs.LG": "llm_agent",
    "cs.HC": "cognition",
    "q-bio.NC": "cognition",
    "physics.soc-ph": "sociology",
}


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_paper(raw: dict | PaperCandidate) -> Paper:
    if is_dataclass(raw):
        raw = asdict(raw)

    title = normalize_text(str(raw.get("title", "")))
    source = str(raw.get("source", "manual"))
    source_url = str(raw.get("source_url") or raw.get("url") or "")
    paper_id = str(raw.get("id") or source_url or title.lower())
    categories = list(raw.get("categories") or [])
    tags = list(raw.get("tags") or [])
    topics = list(raw.get("topics") or _infer_topics(categories, tags))
    published_date = raw.get("published_date") or raw.get("published_at")
    identifiers = dict(raw.get("identifiers") or {})
    if source == "arxiv" and paper_id and "arxiv_id" not in identifiers:
        identifiers["arxiv_id"] = paper_id.replace("arxiv:", "")

    return Paper(
        id=paper_id,
        title=title,
        source=source,
        topics=topics,
        url=str(raw.get("url") or source_url),
        source_url=source_url,
        title_zh=raw.get("title_zh"),
        field=raw.get("field"),
        source_type=raw.get("source_type"),
        recommendation_level=raw.get("recommendation_level"),
        reading_advice=raw.get("reading_advice"),
        code_url=raw.get("code_url"),
        project_url=raw.get("project_url"),
        citation_count=raw.get("citation_count"),
        venue=raw.get("venue"),
        difficulty=raw.get("difficulty"),
        why_recommended=raw.get("why_recommended"),
        classic_status=raw.get("classic_status"),
        selected_for_s_level=bool(raw.get("selected_for_s_level", False)),
        score=raw.get("score"),
        authors=list(raw.get("authors") or []),
        institutions=list(raw.get("institutions") or []),
        categories=categories,
        tags=tags,
        abstract=normalize_text(str(raw.get("abstract", ""))),
        pdf_url=raw.get("pdf_url"),
        published_date=published_date,
        published_at=published_date,
        identifiers=identifiers,
        scores=dict(raw.get("scores") or {}),
        reading_status=str(raw.get("reading_status", "backlog")),
    )


def normalize_papers(raw_papers: list[dict | PaperCandidate]) -> list[Paper]:
    return [normalize_paper(raw) for raw in raw_papers]


def _infer_topics(categories: list[str], tags: list[str]) -> list[str]:
    topics: list[str] = []
    for value in [*categories, *tags]:
        topic = CATEGORY_TOPIC_MAP.get(value)
        if topic and topic not in topics:
            topics.append(topic)
    return topics or ["uncategorized"]
