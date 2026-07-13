from __future__ import annotations

from dataclasses import replace
from datetime import date
from math import log1p
from typing import Any

from paper_learning.core.models import Paper
from paper_learning.utils.config import DEFAULT_RANKING_WEIGHTS, DEFAULT_SOURCE_QUALITY

SOURCE_QUALITY = dict(DEFAULT_SOURCE_QUALITY)

ENGINEERING_CATEGORIES = {"cs.AR", "cs.DC", "cs.GR", "cs.SE", "cs.PL", "cs.PF"}
TOP_VENUE_KEYWORDS = {"ICLR", "NEURIPS", "ICML", "COLM", "ACL", "EMNLP", "SIGGRAPH", "ISCA", "MICRO"}


def _get(paper: Any, key: str, default: Any = None) -> Any:
    if isinstance(paper, dict):
        return paper.get(key, default)
    return getattr(paper, key, default)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def score_factors(
    paper: Any,
    *,
    report_date: str | None = None,
    source_quality_config: dict[str, float] | None = None,
) -> dict[str, float]:
    scores = dict(_get(paper, "scores", {}) or {})
    topics = list(_get(paper, "topics", []) or [])
    categories = set(_get(paper, "categories", []) or [])
    tags = set(_get(paper, "tags", []) or [])
    source = str(_get(paper, "source", "manual"))
    source_type = _get(paper, "source_type", None)
    citation_count = _get(paper, "citation_count")
    influential_citation_count = _get(paper, "influential_citation_count")
    venue = _get(paper, "venue")
    field = _get(paper, "field")
    enrichment_sources = set(_get(paper, "enrichment_sources", []) or [])

    user_relevance = float(scores.get("user_relevance", scores.get("topic_match", 0.75 if topics else 0.25)))
    if "engineering_transferability" in scores:
        engineering_transferability = float(scores["engineering_transferability"])
    else:
        engineering_transferability = float(
            scores.get(
                "implementation_signal",
                0.80 if categories & ENGINEERING_CATEGORIES or tags & {"gpu_graphics", "architecture"} else 0.45,
            )
        )
        if _get(paper, "code_url") or _get(paper, "project_url"):
            engineering_transferability += 0.15
        if venue:
            engineering_transferability += 0.03

    classic_value = float(scores.get("classic_value", 1.0 if source_type == "classic" else 0.35))
    if source_type != "classic":
        classic_value = max(classic_value, 0.35 + 0.25 * _citation_signal(citation_count))

    return {
        "recency": float(scores.get("recency", _recency_score(source_type, _get(paper, "published_date"), report_date))),
        "user_relevance": user_relevance,
        "source_quality": float(
            scores.get(
                "source_quality",
                _source_quality_score(
                    source=source,
                    source_type=source_type,
                    enrichment_sources=enrichment_sources,
                    citation_count=citation_count,
                    influential_citation_count=influential_citation_count,
                    venue=venue,
                    field=field,
                    source_quality_config=source_quality_config,
                ),
            )
        ),
        "engineering_transferability": engineering_transferability,
        "classic_value": classic_value,
    }


def score_paper(
    paper: Any,
    weights: dict[str, float] | None = None,
    *,
    report_date: str | None = None,
    source_quality_config: dict[str, float] | None = None,
) -> float:
    """Return a deterministic score without network access."""

    active_weights = weights or DEFAULT_RANKING_WEIGHTS
    factors = score_factors(paper, report_date=report_date, source_quality_config=source_quality_config)
    total_weight = sum(active_weights.values()) or 1.0
    total = sum(_clamp(factors[name]) * weight for name, weight in active_weights.items())
    return round(_clamp(total / total_weight), 4)


def rank_papers(
    papers: list[Any],
    weights: dict[str, float] | None = None,
    *,
    report_date: str | None = None,
    source_quality_config: dict[str, float] | None = None,
) -> list[Any]:
    return sorted(
        papers,
        key=lambda paper: score_paper(
            paper,
            weights,
            report_date=report_date,
            source_quality_config=source_quality_config,
        ),
        reverse=True,
    )


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
    source_quality_config = ranking_config.get("source_quality") or SOURCE_QUALITY
    ranked = rank_papers(papers, weights, report_date=report_date, source_quality_config=source_quality_config)
    ranked = _apply_group_targets(
        ranked,
        max_daily=max_daily,
        weights=weights,
        report_date=report_date,
        ranking_config=ranking_config,
        source_quality_config=source_quality_config,
        group_targets=group_targets or {},
    )

    selected: list[Paper] = []
    s_count = 0
    for paper in ranked:
        factors = score_factors(paper, report_date=report_date, source_quality_config=source_quality_config)
        score = score_paper(
            paper,
            weights,
            report_date=report_date,
            source_quality_config=source_quality_config,
        )
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
    source_quality_config: dict[str, float],
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
            and score_paper(
                paper,
                weights,
                report_date=report_date,
                source_quality_config=source_quality_config,
            )
            >= min_score
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


def _source_quality_score(
    *,
    source: str,
    source_type: str | None,
    enrichment_sources: set[str],
    citation_count: object,
    influential_citation_count: object,
    venue: object,
    field: object,
    source_quality_config: dict[str, float] | None,
) -> float:
    config = source_quality_config or SOURCE_QUALITY
    source_key = "manual_classic" if source_type == "classic" else source
    base = float(config.get(source_key, SOURCE_QUALITY.get(source_key, 0.50)))
    if "semantic_scholar" in enrichment_sources:
        base = max(base, float(config.get("semantic_scholar_enriched", base)))
    base += 0.06 * _citation_signal(citation_count)
    base += 0.04 * _citation_signal(influential_citation_count, denominator=100)
    if _is_top_venue(venue):
        base += 0.03
    if field:
        base += 0.01
    return _clamp(base)


def _citation_signal(value: object, *, denominator: int = 1000) -> float:
    try:
        count = int(value or 0)
    except (TypeError, ValueError):
        return 0.0
    if count <= 0:
        return 0.0
    return _clamp(log1p(count) / log1p(denominator))


def _is_top_venue(value: object) -> bool:
    venue = str(value or "").upper()
    return any(keyword in venue for keyword in TOP_VENUE_KEYWORDS)


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
