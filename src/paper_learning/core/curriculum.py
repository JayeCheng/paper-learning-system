from __future__ import annotations

from pathlib import Path
from typing import Any

from paper_learning.core.models import PaperCandidate
from paper_learning.utils.config import load_classic_items, slugify


def _paper_id(paper: Any) -> str:
    if isinstance(paper, dict):
        return str(paper.get("id", ""))
    return str(getattr(paper, "id", ""))


def recommend_next_readings(
    ranked_papers: list[Any],
    reading_status: dict[str, str] | None = None,
    *,
    limit: int = 3,
) -> list[Any]:
    status = reading_status or {}
    blocked = {"deep_read", "archived", "skipped"}
    recommendations: list[Any] = []

    for paper in ranked_papers:
        if status.get(_paper_id(paper), "backlog") in blocked:
            continue
        recommendations.append(paper)
        if len(recommendations) >= limit:
            break

    return recommendations


def load_classic_fallback_candidates(
    limit: int,
    *,
    existing_count: int = 0,
    curriculum_dir: Path = Path("curriculum"),
) -> list[PaperCandidate]:
    needed = max(0, limit - existing_count)
    if needed == 0:
        return []

    candidates: list[PaperCandidate] = []
    for item in load_classic_items(curriculum_dir):
        track = str(item.get("track", "classic"))
        title = str(item.get("title", "Untitled classic"))
        reason = str(item.get("reason", "Classic paper candidate."))
        status = str(item.get("status", "candidate"))
        candidates.append(
            PaperCandidate(
                id=f"classic:{track}:{slugify(title)}",
                title=title,
                authors=[],
                abstract=reason,
                source="manual",
                source_url=f"https://github.com/JayeCheng/paper-learning-system/blob/main/curriculum/{track}_classics.yaml",
                pdf_url=None,
                published_date=None,
                categories=[track],
                tags=["classic", track],
                source_type="classic",
                source_group=track,
                identifiers={},
                field=track,
                classic_status=status,
            )
        )
        if len(candidates) >= needed:
            break
    return candidates
