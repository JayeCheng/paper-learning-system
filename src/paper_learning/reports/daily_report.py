from __future__ import annotations

import csv
import json
from dataclasses import replace
from pathlib import Path

from paper_learning.core.models import DailyReport, Paper
from paper_learning.reports.json_renderer import render_daily_json
from paper_learning.reports.markdown_renderer import render_daily_markdown
from paper_learning.utils.time import today_string, utc_now_string

PUBLIC_JSON_VERSION = "0.1"


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
        learning_route_position="v0.1 daily radar MVP",
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


def write_daily_report(
    report: DailyReport,
    *,
    markdown_path: Path | None = None,
    json_path: Path | None = None,
    public_dir: Path = Path("data/public"),
    exports_dir: Path = Path("data/exports"),
) -> tuple[Path, Path]:
    default_markdown_path, default_json_path = daily_report_paths(report.date)
    markdown_path = markdown_path or default_markdown_path
    json_path = json_path or default_json_path
    latest_path = public_dir / "latest.json"
    daily_index_path = public_dir / "daily_index.json"
    papers_index_path = public_dir / "papers_index.json"
    knowledge_graph_path = public_dir / "knowledge_graph.json"

    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    public_dir.mkdir(parents=True, exist_ok=True)
    exports_dir.mkdir(parents=True, exist_ok=True)

    report_with_paths = replace(
        report,
        generated_paths={
            "markdown": markdown_path.as_posix(),
            "json": json_path.as_posix(),
            "public_latest": latest_path.as_posix(),
            "public_daily_index": daily_index_path.as_posix(),
            "public_papers_index": papers_index_path.as_posix(),
            "public_knowledge_graph": knowledge_graph_path.as_posix(),
            "exports_jsonl": (exports_dir / "papers.jsonl").as_posix(),
            "exports_csv": (exports_dir / "papers.csv").as_posix(),
            "exports_reading_status": (exports_dir / "reading_status.csv").as_posix(),
        },
        frontend_entry=latest_path.as_posix(),
    )

    markdown_path.write_text(render_daily_markdown(report_with_paths), encoding="utf-8")
    json_path.write_text(render_daily_json(report_with_paths), encoding="utf-8")
    _write_public_json(report_with_paths, markdown_path, json_path, public_dir)
    _write_exports(report_with_paths, exports_dir)
    return markdown_path, json_path


def _source_mode_summary(papers: list[Paper]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for paper in papers:
        source_type = paper.source_type or "unspecified"
        summary[source_type] = summary.get(source_type, 0) + 1
    return summary


def _write_public_json(report: DailyReport, markdown_path: Path, json_path: Path, public_dir: Path) -> None:
    latest_entry = {
        "date": report.date,
        "generated_at": report.generated_at,
        "markdown_path": markdown_path.as_posix(),
        "json_path": json_path.as_posix(),
        "paper_count": len(report.papers),
        "s_level_paper_id": report.s_level_paper_id,
    }
    latest_payload = {
        "public_json_version": report.public_json_version,
        "frontend_entry": "data/public/latest.json",
        "latest": latest_entry,
    }
    index_payload = _daily_index_payload(public_dir / "daily_index.json", report, latest_entry)
    papers_payload = _papers_index_payload(public_dir / "papers_index.json", report)
    graph_payload = _knowledge_graph_payload(report)

    _write_json(public_dir / "latest.json", latest_payload)
    _write_json(public_dir / "daily_index.json", index_payload)
    _write_json(public_dir / "papers_index.json", papers_payload)
    _write_json(public_dir / "knowledge_graph.json", graph_payload)


def _daily_index_payload(path: Path, report: DailyReport, latest_entry: dict) -> dict:
    reports = []
    if path.exists():
        reports = [entry for entry in _read_json(path).get("reports", []) if entry.get("date") != report.date]
    reports.append(latest_entry)
    reports.sort(key=lambda entry: entry["date"], reverse=True)
    return {
        "public_json_version": report.public_json_version,
        "latest": latest_entry,
        "reports": reports,
    }


def _papers_index_payload(path: Path, report: DailyReport) -> dict:
    paper_map = {}
    if path.exists():
        for paper in _read_json(path).get("papers", []):
            paper_map[paper["id"]] = paper
    for paper in report.papers:
        paper_map[paper.id] = paper.to_dict()
    return {
        "public_json_version": report.public_json_version,
        "updated_at": report.generated_at,
        "papers": sorted(paper_map.values(), key=lambda item: item["id"]),
    }


def _knowledge_graph_payload(report: DailyReport) -> dict:
    nodes = []
    edges = []
    topic_ids: set[str] = set()
    for paper in report.papers:
        nodes.append({"id": paper.id, "label": paper.title, "type": "paper", "topics": paper.topics})
        for topic in paper.topics:
            topic_ids.add(topic)
            edges.append({"source": paper.id, "target": topic, "relation": "related_to", "confidence": 0.5})
    nodes.extend({"id": topic, "label": topic, "type": "concept", "topics": [topic]} for topic in sorted(topic_ids))
    return {
        "public_json_version": report.public_json_version,
        "updated_at": report.generated_at,
        "nodes": nodes,
        "edges": edges,
    }


def _write_exports(report: DailyReport, exports_dir: Path) -> None:
    paper_rows = [paper.to_dict() for paper in report.papers]
    jsonl_path = exports_dir / "papers.jsonl"
    csv_path = exports_dir / "papers.csv"
    reading_status_path = exports_dir / "reading_status.csv"

    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in paper_rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    _write_csv(csv_path, paper_rows, ["id", "title", "source", "source_type", "recommendation_level", "score", "url"])
    _write_csv(
        reading_status_path,
        [
            {
                "paper_id": paper.id,
                "status": paper.reading_status,
                "priority": "s_level" if paper.selected_for_s_level else "medium",
                "recommendation_level": paper.recommendation_level,
                "updated_at": report.generated_at,
                "title": paper.title,
            }
            for paper in report.papers
        ],
        ["paper_id", "status", "priority", "recommendation_level", "updated_at", "title"],
    )


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError):
        return {}
