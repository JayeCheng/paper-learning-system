from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from paper_learning.core.curriculum import load_classic_fallback_candidates
from paper_learning.core.dedupe import dedupe_papers
from paper_learning.core.models import DailyReport
from paper_learning.core.normalize import normalize_papers
from paper_learning.core.rank import select_ranked_papers
from paper_learning.fetchers.arxiv_fetcher import fetch_arxiv_candidates
from paper_learning.reports.daily_report import build_daily_report, write_daily_report
from paper_learning.utils.config import load_arxiv_source_config, load_ranking_config
from paper_learning.utils.time import today_string


def resolve_report_date(value: str | None) -> str:
    if value in (None, "", "today"):
        return today_string()
    datetime.strptime(value, "%Y-%m-%d")
    return value


def run_daily_pipeline(date: str | None = None, *, root: Path = Path(".")) -> tuple[DailyReport, Path, Path]:
    report_date = resolve_report_date(date)
    arxiv_config = load_arxiv_source_config(root / "config/sources.yaml")
    ranking_config = load_ranking_config(root / "config/ranking.yaml")
    max_daily = int(ranking_config.get("max_daily_papers", 6))

    recent_candidates = []
    now = datetime.now(timezone.utc)
    for source_type, window_days in arxiv_config["windows"].items():
        recent_candidates.extend(
            fetch_arxiv_candidates(
                categories=arxiv_config["categories"],
                source_type=source_type,
                window_days=window_days,
                max_results=int(arxiv_config.get("max_results_per_window", 40)),
                now=now,
            )
        )

    unique_papers = build_candidate_pool(
        recent_candidates,
        max_daily=max_daily,
        curriculum_dir=root / "curriculum",
    )
    selected = select_ranked_papers(unique_papers, ranking_config=ranking_config, report_date=report_date)

    report = build_daily_report(selected, date=report_date, summary=_summary(selected))
    markdown_path, json_path = write_daily_report(report)
    return report, markdown_path, json_path


def build_candidate_pool(recent_candidates: list, *, max_daily: int, curriculum_dir: Path = Path("curriculum")) -> list:
    recent_papers = dedupe_papers(normalize_papers(recent_candidates))
    if len(recent_papers) >= max_daily:
        return recent_papers

    classic_candidates = load_classic_fallback_candidates(
        max_daily,
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
