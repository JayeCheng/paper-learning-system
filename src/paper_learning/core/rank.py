from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import Any

from paper_learning.core.models import Paper
from paper_learning.utils.config import DEFAULT_RANKING_WEIGHTS

SOURCE_QUALITY = {
    "openreview": 0.85,
    "arxiv": 0.78,
    "biorxiv": 0.70,
    "semantic_scholar": 0.65,
    "github": 0.60,
    "manual": 0.55,
}

ENGINEERING_CATEGORIES = {"cs.AR", "cs.DC", "cs.GR", "cs.SE", "cs.PL", "cs.PF"}


def _get(paper: Any, key: str, default: Any = None) -> Any:
    if isinstance(paper, dict):
        return paper.get(key, default)
    return getattr(paper, key, default)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def score_factors(paper: Any, *, report_date: str | None = None) -> dict[str, float]:
    scores = dict(_get(paper, "scores", {}) or {})
    topics = list(_get(paper, "topics", []) or [])
    categories = set(_get(paper, "categories", []) or [])
    tags = set(_get(paper, "tags", []) or [])
    source = str(_get(paper, "source", "manual"))
    source_type = _get(paper, "source_type", None)

    user_relevance = float(scores.get("user_relevance", scores.get("topic_match", 0.75 if topics else 0.25)))
    engineering_transferability = float(
        scores.get(
            "engineering_transferability",
            scores.get(
                "implementation_signal",
                0.80 if categories & ENGINEERING_CATEGORIES or tags & {"gpu_graphics", "architecture"} else 0.45,
            ),
        )
    )

    return {
        "recency": float(scores.get("recency", _recency_score(source_type, _get(paper, "published_date"), report_date))),
        "user_relevance": user_relevance,
        "source_quality": float(scores.get("source_quality", SOURCE_QUALITY.get(source, 0.50))),
        "engineering_transferability": engineering_transferability,
        "classic_value": float(scores.get("classic_value", 1.0 if source_type == "classic" else 0.35)),
    }


def score_paper(
    paper: Any,
    weights: dict[str, float] | None = None,
    *,
    report_date: str | None = None,
) -> float:
    """Return a deterministic score without network access."""

    active_weights = weights or DEFAULT_RANKING_WEIGHTS
    factors = score_factors(paper, report_date=report_date)
    total_weight = sum(active_weights.values()) or 1.0
    total = sum(_clamp(factors[name]) * weight for name, weight in active_weights.items())
    return round(_clamp(total / total_weight), 4)


def rank_papers(
    papers: list[Any],
    weights: dict[str, float] | None = None,
    *,
    report_date: str | None = None,
) -> list[Any]:
    return sorted(papers, key=lambda paper: score_paper(paper, weights, report_date=report_date), reverse=True)


def select_ranked_papers(
    papers: list[Paper],
    *,
    ranking_config: dict,
    report_date: str,
    group_targets: dict[str, int] | None = None,
) -> list[Paper]:
    max_daily = int(ranking_config.get("max_daily_papers", 6))
    max_s_level = int(ranking_config.get("max_s_level_papers", 1))
    weights = ranking_config.get("weights") or DEFAULT_RANKING_WEIGHTS
    ranked = rank_papers(papers, weights, report_date=report_date)
    ranked = _apply_group_targets(
        ranked,
        max_daily=max_daily,
        weights=weights,
        report_date=report_date,
        ranking_config=ranking_config,
        group_targets=group_targets or {},
    )

    selected: list[Paper] = []
    s_count = 0
    for paper in ranked:
        factors = score_factors(paper, report_date=report_date)
        score = score_paper(paper, weights, report_date=report_date)
        level = _recommendation_level(score, ranking_config)
        selected_for_s = level == "S" and s_count < max_s_level
        if level == "S" and not selected_for_s:
            level = "A"
        if selected_for_s:
            s_count += 1
        selected.append(
            replace(
                paper,
                score=score,
                scores={**factors, "total": score},
                recommendation_level=level,
                selected_for_s_level=selected_for_s,
                reading_advice=_reading_advice(level),
                why_recommended=_why_recommended(paper, factors),
            )
        )
    return selected


def _apply_group_targets(
    ranked: list[Paper],
    *,
    max_daily: int,
    weights: dict[str, float],
    report_date: str,
    ranking_config: dict,
    group_targets: dict[str, int],
) -> list[Paper]:
    if not group_targets:
        return ranked[:max_daily]

    min_score = float(ranking_config.get("group_min_score", ranking_config.get("b_level_threshold", 0.58)))
    selected: list[Paper] = []
    selected_ids: set[str] = set()

    for group_name, target in group_targets.items():
        if target <= 0 or len(selected) >= max_daily:
            continue
        group_papers = [
            paper
            for paper in ranked
            if paper.id not in selected_ids
            and _paper_group(paper) == group_name
            and score_paper(paper, weights, report_date=report_date) >= min_score
        ]
        for paper in group_papers[:target]:
            selected.append(paper)
            selected_ids.add(paper.id)
            if len(selected) >= max_daily:
                break

    for paper in ranked:
        if len(selected) >= max_daily:
            break
        if paper.id in selected_ids:
            continue
        selected.append(paper)
        selected_ids.add(paper.id)

    return selected


def _paper_group(paper: Paper) -> str | None:
    if paper.source_group:
        return paper.source_group
    if paper.field:
        return paper.field
    return paper.topics[0] if paper.topics else None


def _recency_score(source_type: str | None, published_date: str | None, report_date: str | None) -> float:
    if source_type == "recent_24h":
        return 1.0
    if source_type == "recent_7d":
        return 0.78
    if source_type == "classic":
        return 0.45
    if not published_date or not report_date:
        return 0.55
    try:
        age_days = (date.fromisoformat(report_date) - date.fromisoformat(published_date[:10])).days
    except ValueError:
        return 0.55
    if age_days <= 1:
        return 1.0
    if age_days <= 7:
        return 0.78
    if age_days <= 30:
        return 0.55
    return 0.35


def _recommendation_level(score: float, ranking_config: dict) -> str:
    if score >= float(ranking_config.get("s_level_threshold", 0.88)):
        return "S"
    if score >= float(ranking_config.get("a_level_threshold", 0.74)):
        return "A"
    if score >= float(ranking_config.get("b_level_threshold", 0.58)):
        return "B"
    return "C"


def _reading_advice(level: str) -> str:
    return {
        "S": "deep_read",
        "A": "quick_read",
        "B": "save_for_later",
        "C": "abstract_only",
    }[level]


def _why_recommended(paper: Paper, factors: dict[str, float]) -> str:
    strongest = max(factors, key=factors.get)
    label = strongest.replace("_", " ")
    if paper.source_type == "classic":
        return f"Classic fallback with strong {label} signal."
    return f"Ranked by {label} signal across configured topics."
