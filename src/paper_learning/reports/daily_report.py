from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from paper_learning.core.models import DailyReport, Paper
from paper_learning.reports.json_renderer import render_daily_json
from paper_learning.reports.markdown_renderer import render_daily_markdown
from paper_learning.utils.time import today_string, utc_now_string

PUBLIC_JSON_VERSION = "0.3"


def daily_report_paths(date: str, *, daily_root: Path = Path("daily")) -> tuple[Path, Path]:
    year, month, _day = date.split("-", maxsplit=2)
    directory = daily_root / year / month
    return directory / f"{date}.md", directory / f"{date}.json"


def build_daily_report(
    papers: list[Paper] | None = None,
    *,
    date: str | None = None,
    summary: str | None = None,
) -> DailyReport:
    report_date = date or today_string()
    paper_list = papers or []
    s_level_id = next((paper.id for paper in paper_list if paper.selected_for_s_level), None)
    return DailyReport(
        date=report_date,
        generated_at=utc_now_string(),
        summary=summary or f"Selected {len(paper_list)} papers for the daily radar.",
        papers=paper_list,
        learning_route_position="v0.3 source enrichment",
        source_mode_summary=_source_mode_summary(paper_list),
        s_level_paper_id=s_level_id,
        public_json_version=PUBLIC_JSON_VERSION,
        s_level_candidate_ids=[s_level_id] if s_level_id else [],
        knowledge_graph_delta=[f"paper:{paper.id}" for paper in paper_list],
        next_actions=[
            "Review S-level candidate",
            "Update reading status after skim",
            "Promote durable concepts into the knowledge graph",
        ],
    )


def with_generated_paths(
    report: DailyReport,
    *,
    markdown_path: Path,
    json_path: Path,
    public_dir: Path = Path("data/public"),
    exports_dir: Path = Path("data/exports"),
    state_dir: Path = Path("data/state"),
    root: Path = Path("."),
) -> DailyReport:
    latest_path = public_dir / "latest.json"
    return replace(
        report,
        generated_paths={
            "markdown": _repo_path(markdown_path, root),
            "json": _repo_path(json_path, root),
            "public_latest": _repo_path(latest_path, root),
            "public_daily_index": _repo_path(public_dir / "daily_index.json", root),
            "public_papers_index": _repo_path(public_dir / "papers_index.json", root),
            "public_knowledge_graph": _repo_path(public_dir / "knowledge_graph.json", root),
            "public_reading_status": _repo_path(public_dir / "reading_status.json", root),
            "public_curriculum_progress": _repo_path(public_dir / "curriculum_progress.json", root),
            "exports_jsonl": _repo_path(exports_dir / "papers.jsonl", root),
            "exports_csv": _repo_path(exports_dir / "papers.csv", root),
            "exports_daily_csv": _repo_path(exports_dir / "daily_papers.csv", root),
            "exports_reading_status": _repo_path(exports_dir / "reading_status.csv", root),
            "state_papers": _repo_path(state_dir / "papers.jsonl", root),
            "state_reading_status": _repo_path(state_dir / "reading_status.json", root),
            "state_run_history": _repo_path(state_dir / "run_history.json", root),
        },
        frontend_entry=_repo_path(latest_path, root),
    )


def write_daily_report(
    report: DailyReport,
    *,
    markdown_path: Path | None = None,
    json_path: Path | None = None,
) -> tuple[Path, Path]:
    default_markdown_path, default_json_path = daily_report_paths(report.date)
    markdown_path = markdown_path or default_markdown_path
    json_path = json_path or default_json_path

    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_daily_markdown(report), encoding="utf-8")
    json_path.write_text(render_daily_json(report), encoding="utf-8")
    return markdown_path, json_path


def _source_mode_summary(papers: list[Paper]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for paper in papers:
        source_type = paper.source_type or "unspecified"
        summary[source_type] = summary.get(source_type, 0) + 1
    return summary


def _repo_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
