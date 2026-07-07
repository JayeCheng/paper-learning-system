from __future__ import annotations

from typing import Any


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
