from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from paper_learning.core.curriculum import load_classic_fallback_candidates
from paper_learning.core.dedupe import dedupe_papers
from paper_learning.core.models import DailyReport
from paper_learning.core.normalize import normalize_papers
from paper_learning.core.rank import select_ranked_papers
from paper_learning.core.state_store import append_run_history, ensure_reading_status_entries, upsert_papers
from paper_learning.enrichers.semantic_scholar import enrich_papers
from paper_learning.fetchers.arxiv_fetcher import fetch_arxiv_candidates
from paper_learning.fetchers.biorxiv_fetcher import fetch_biorxiv_candidates
from paper_learning.fetchers.openreview_fetcher import fetch_openreview_candidates
from paper_learning.reports.daily_report import build_daily_report, daily_report_paths, with_generated_paths, write_daily_report
from paper_learning.reports.exports import write_exports
from paper_learning.reports.public_json import write_public_json
from paper_learning.utils.config import (
    load_arxiv_source_config,
    load_biorxiv_source_config,
    load_openreview_source_config,
    load_ranking_config,
    load_semantic_scholar_source_config,
)
from paper_learning.utils.time import today_string


def resolve_report_date(value: str | None) -> str:
    if value in (None, "", "today"):
        return today_string()
    datetime.strptime(value, "%Y-%m-%d")
    return value


def run_daily_pipeline(date: str | None = None, *, root: Path = Path(".")) -> tuple[DailyReport, Path, Path]:
    report_date = resolve_report_date(date)
    sources_path = root / "config/sources.yaml"
    arxiv_config = load_arxiv_source_config(sources_path)
    openreview_config = load_openreview_source_config(sources_path)
    biorxiv_config = load_biorxiv_source_config(sources_path)
    semantic_config = load_semantic_scholar_source_config(sources_path)
    ranking_config = load_ranking_config(root / "config/ranking.yaml")
    max_daily = int(ranking_config.get("max_daily_papers", 6))

    recent_candidates = fetch_recent_candidates_by_group(arxiv_config)
    recent_candidates.extend(fetch_openreview_candidates_by_config(openreview_config))
    recent_candidates.extend(fetch_biorxiv_candidates_by_config(biorxiv_config))

    unique_papers = build_candidate_pool(
        recent_candidates,
        max_daily=max_daily,
        classic_pool_limit=max_daily * 4,
        curriculum_dir=root / "curriculum",
    )
    enriched_papers = enrich_papers(unique_papers, semantic_config=semantic_config)
    selected = select_ranked_papers(
        enriched_papers,
        ranking_config=ranking_config,
        report_date=report_date,
        group_targets=_source_group_targets(arxiv_config),
    )

    report = build_daily_report(selected, date=report_date, summary=_summary(selected))
    markdown_path, json_path = daily_report_paths(report.date, daily_root=root / "daily")
    report = with_generated_paths(
        report,
        markdown_path=markdown_path,
        json_path=json_path,
        public_dir=root / "data" / "public",
        exports_dir=root / "data" / "exports",
        state_dir=root / "data" / "state",
        root=root,
    )
    write_daily_report(report, markdown_path=markdown_path, json_path=json_path)

    all_papers = upsert_papers(report.papers, root=root)
    reading_statuses = ensure_reading_status_entries(report.papers, root=root, updated_at=report.generated_at)
    run_history = append_run_history(
        root=root,
        date=report.date,
        generated_at=report.generated_at,
        generated_paths=report.generated_paths,
        paper_count=len(report.papers),
        s_level_paper_id=report.s_level_paper_id,
        status="success",
    )
    write_exports(
        papers=all_papers,
        reading_statuses=reading_statuses,
        daily_papers=report.papers,
        exports_dir=root / "data" / "exports",
    )
    write_public_json(
        report=report,
        papers=all_papers,
        reading_statuses=reading_statuses,
        run_history=run_history,
        public_dir=root / "data" / "public",
    )
    return report, markdown_path, json_path


def fetch_recent_candidates_by_group(arxiv_config: dict, *, now: datetime | None = None) -> list:
    candidates = []
    timestamp = now or datetime.now(timezone.utc)
    source_groups = arxiv_config.get("source_groups") or {
        "default": {
            "categories": arxiv_config.get("categories", []),
            "max_results_per_window": arxiv_config.get("max_results_per_window", 40),
        }
    }
    for source_type, window_days in arxiv_config["windows"].items():
        for group_name, group_config in source_groups.items():
            candidates.extend(
                fetch_arxiv_candidates(
                    categories=list(group_config.get("categories") or arxiv_config.get("categories") or []),
                    source_type=source_type,
                    source_group=group_name,
                    window_days=window_days,
                    max_results=int(group_config.get("max_results_per_window", arxiv_config.get("max_results_per_window", 40))),
                    now=timestamp,
                )
            )
    return candidates


def fetch_openreview_candidates_by_config(openreview_config: dict) -> list:
    if not openreview_config.get("enabled", False):
        return []
    return fetch_openreview_candidates(
        venues=_as_string_list(openreview_config.get("venues")),
        venue_ids=_as_string_list(openreview_config.get("venue_ids")),
        years=[int(value) for value in _as_string_list(openreview_config.get("years"))],
        limit=int(openreview_config.get("max_results_per_venue", 10)),
    )


def fetch_biorxiv_candidates_by_config(biorxiv_config: dict, *, now: datetime | None = None) -> list:
    if not biorxiv_config.get("enabled", False):
        return []
    return fetch_biorxiv_candidates(
        query=str(biorxiv_config.get("query") or "") or None,
        categories=_as_string_list(biorxiv_config.get("categories")),
        servers=_as_string_list(biorxiv_config.get("servers")),
        window_days=int(biorxiv_config.get("window_days", 7)),
        limit=int(biorxiv_config.get("max_results", 20)),
        now=now,
    )


def build_candidate_pool(
    recent_candidates: list,
    *,
    max_daily: int,
    classic_pool_limit: int | None = None,
    curriculum_dir: Path = Path("curriculum"),
) -> list:
    recent_papers = dedupe_papers(normalize_papers(recent_candidates))
    if len(recent_papers) >= max_daily:
        return recent_papers

    fallback_limit = classic_pool_limit or max_daily
    classic_candidates = load_classic_fallback_candidates(
        fallback_limit,
        existing_count=len(recent_papers),
        curriculum_dir=curriculum_dir,
    )
    classic_papers = normalize_papers(classic_candidates)
    return dedupe_papers([*recent_papers, *classic_papers])


def _summary(papers: list) -> str:
    if not papers:
        return "No paper candidates were selected. Check source connectivity or curriculum fallback."
    recent_count = sum(1 for paper in papers if paper.source_type in {"recent_24h", "recent_7d"})
    classic_count = sum(1 for paper in papers if paper.source_type == "classic")
    return f"Selected {len(papers)} papers: {recent_count} recent candidates and {classic_count} classic fallback items."


def _source_group_targets(arxiv_config: dict) -> dict[str, int]:
    return {
        name: int(group.get("target_min_daily", 0))
        for name, group in (arxiv_config.get("source_groups") or {}).items()
        if int(group.get("target_min_daily", 0)) > 0
    }


def _as_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item)]
    if isinstance(value, str):
        return [value] if value else []
    return [str(value)]
