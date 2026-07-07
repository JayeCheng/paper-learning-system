from __future__ import annotations

import math
from typing import Any

DEFAULT_WEIGHTS = {
    "topic_match": 0.30,
    "source_quality": 0.20,
    "recency": 0.15,
    "citation_signal": 0.15,
    "implementation_signal": 0.10,
    "curriculum_fit": 0.10,
}

SOURCE_QUALITY = {
    "openreview": 0.85,
    "arxiv": 0.75,
    "biorxiv": 0.70,
    "semantic_scholar": 0.65,
    "github": 0.55,
    "manual": 0.50,
}


def _get(paper: Any, key: str, default: Any = None) -> Any:
    if isinstance(paper, dict):
        return paper.get(key, default)
    return getattr(paper, key, default)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def score_paper(paper: Any, weights: dict[str, float] | None = None) -> float:
    """Return a deterministic score without network access."""

    active_weights = weights or DEFAULT_WEIGHTS
    scores = dict(_get(paper, "scores", {}) or {})
    topics = list(_get(paper, "topics", []) or [])
    source = str(_get(paper, "source", "manual"))
    citations = float(scores.get("citations", 0.0))

    features = {
        "topic_match": scores.get("topic_match", 0.75 if topics else 0.0),
        "source_quality": scores.get("source_quality", SOURCE_QUALITY.get(source, 0.50)),
        "recency": scores.get("recency", 0.50),
        "citation_signal": scores.get("citation_signal", _clamp(math.log10(citations + 1) / 4)),
        "implementation_signal": scores.get(
            "implementation_signal",
            0.70 if source == "github" else 0.20,
        ),
        "curriculum_fit": scores.get("curriculum_fit", 0.50),
    }

    total = sum(_clamp(float(features[name])) * weight for name, weight in active_weights.items())
    return round(_clamp(total), 4)


def rank_papers(papers: list[Any], weights: dict[str, float] | None = None) -> list[Any]:
    return sorted(papers, key=lambda paper: score_paper(paper, weights), reverse=True)
