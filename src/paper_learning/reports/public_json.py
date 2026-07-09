from __future__ import annotations

import json
from pathlib import Path

from paper_learning.core.models import DailyReport, Paper, ReadingStatus
from paper_learning.core.state_store import apply_reading_statuses

TRACK_LABELS = {
    "gpu_graphics": "GPU / Graphics",
    "architecture": "Computer Architecture",
    "llm_agent": "LLM Agent / RAG",
    "cognition": "Cognitive Science",
    "sociology": "Sociology",
    "cognition_social": "Cognition / Social Systems",
}


def write_public_json(
    *,
    report: DailyReport | None,
    papers: list[Paper],
    reading_statuses: dict[str, ReadingStatus],
    run_history: list[dict],
    public_dir: Path = Path("data/public"),
) -> dict[str, Path]:
    public_dir.mkdir(parents=True, exist_ok=True)
    updated_at = _updated_at(report, run_history)
    version = report.public_json_version if report else "0.2"
    papers_with_status = apply_reading_statuses(papers, reading_statuses)
    latest_entry = _latest_entry(report, run_history)

    payloads = {
        "latest": {
            "public_json_version": version,
            "frontend_entry": "data/public/latest.json",
            "latest": latest_entry,
        },
        "daily_index": _daily_index_payload(version, latest_entry, run_history),
        "papers_index": _papers_index_payload(version, updated_at, papers_with_status),
        "knowledge_graph": _knowledge_graph_payload(version, updated_at, papers_with_status),
        "reading_status": _reading_status_payload(version, updated_at, reading_statuses),
        "curriculum_progress": _curriculum_progress_payload(version, updated_at, papers_with_status, reading_statuses),
    }

    paths = {
        "latest": public_dir / "latest.json",
        "daily_index": public_dir / "daily_index.json",
        "papers_index": public_dir / "papers_index.json",
        "knowledge_graph": public_dir / "knowledge_graph.json",
        "reading_status": public_dir / "reading_status.json",
        "curriculum_progress": public_dir / "curriculum_progress.json",
    }
    for name, path in paths.items():
        _write_json(path, payloads[name])
    return paths


def _updated_at(report: DailyReport | None, run_history: list[dict]) -> str:
    if report:
        return report.generated_at
    if run_history:
        return str(run_history[-1].get("generated_at") or run_history[-1].get("updated_at") or "")
    return ""


def _latest_entry(report: DailyReport | None, run_history: list[dict]) -> dict | None:
    if report:
        return _run_to_public_entry(
            {
                "date": report.date,
                "generated_at": report.generated_at,
                "generated_paths": report.generated_paths,
                "paper_count": len(report.papers),
                "s_level_paper_id": report.s_level_paper_id,
                "status": "success",
            }
        )
    for run in reversed(run_history):
        if run.get("status") == "success":
            return _run_to_public_entry(run)
    return None


def _daily_index_payload(version: str, latest_entry: dict | None, run_history: list[dict]) -> dict:
    reports_by_date: dict[str, dict] = {}
    for run in run_history:
        if run.get("status") != "success" or not run.get("date"):
            continue
        reports_by_date[str(run["date"])] = _run_to_public_entry(run)
    reports = sorted(reports_by_date.values(), key=lambda entry: entry["date"], reverse=True)
    return {
        "public_json_version": version,
        "latest": latest_entry,
        "reports": reports,
    }


def _run_to_public_entry(run: dict) -> dict:
    paths = dict(run.get("generated_paths") or {})
    return {
        "date": run.get("date"),
        "generated_at": run.get("generated_at"),
        "markdown_path": paths.get("markdown"),
        "json_path": paths.get("json"),
        "paper_count": int(run.get("paper_count") or 0),
        "s_level_paper_id": run.get("s_level_paper_id"),
        "status": run.get("status", "success"),
    }


def _papers_index_payload(version: str, updated_at: str, papers: list[Paper]) -> dict:
    return {
        "public_json_version": version,
        "updated_at": updated_at,
        "papers": [paper.to_dict() for paper in sorted(papers, key=lambda item: item.id)],
    }


def _knowledge_graph_payload(version: str, updated_at: str, papers: list[Paper]) -> dict:
    nodes = []
    edges = []
    topic_ids: set[str] = set()
    for paper in sorted(papers, key=lambda item: item.id):
        nodes.append({"id": paper.id, "label": paper.title, "type": "paper", "topics": paper.topics})
        for topic in paper.topics:
            topic_ids.add(topic)
            edges.append({"source": paper.id, "target": topic, "relation": "related_to", "confidence": 0.5})
        if paper.source_group and paper.source_group not in paper.topics:
            topic_ids.add(paper.source_group)
            edges.append({"source": paper.id, "target": paper.source_group, "relation": "related_to", "confidence": 0.5})
    nodes.extend({"id": topic, "label": topic, "type": "concept", "topics": [topic]} for topic in sorted(topic_ids))
    return {
        "public_json_version": version,
        "updated_at": updated_at,
        "nodes": nodes,
        "edges": edges,
    }


def _reading_status_payload(version: str, updated_at: str, statuses: dict[str, ReadingStatus]) -> dict:
    return {
        "public_json_version": version,
        "updated_at": updated_at,
        "statuses": [statuses[paper_id].to_dict() for paper_id in sorted(statuses)],
    }


def _curriculum_progress_payload(
    version: str,
    updated_at: str,
    papers: list[Paper],
    statuses: dict[str, ReadingStatus],
) -> dict:
    track_map: dict[str, list[Paper]] = {}
    for paper in papers:
        for track in _paper_tracks(paper):
            track_map.setdefault(track, []).append(paper)

    tracks = []
    for track_id in sorted(track_map):
        track_papers = sorted(track_map[track_id], key=lambda paper: (-(paper.score or 0), paper.id))
        completed = [
            paper
            for paper in track_papers
            if statuses.get(paper.id) and statuses[paper.id].status in {"deep_read", "archived"}
        ]
        active = [
            paper
            for paper in track_papers
            if statuses.get(paper.id) and statuses[paper.id].status in {"queued", "skimmed"}
        ]
        next_papers = [
            paper
            for paper in track_papers
            if not statuses.get(paper.id) or statuses[paper.id].status in {"backlog", "queued"}
        ][:3]
        tracks.append(
            {
                "id": track_id,
                "label": TRACK_LABELS.get(track_id, track_id.replace("_", " ").title()),
                "completed_count": len(completed),
                "planned_count": len(track_papers),
                "current_position": active[0].id if active else None,
                "next_paper_ids": [paper.id for paper in next_papers],
            }
        )

    return {
        "public_json_version": version,
        "updated_at": updated_at,
        "tracks": tracks,
    }


def _paper_tracks(paper: Paper) -> list[str]:
    tracks = []
    if paper.source_group:
        tracks.append(paper.source_group)
    for topic in paper.topics:
        if topic == "uncategorized" and tracks:
            continue
        if topic not in tracks:
            tracks.append(topic)
    return tracks or ["uncategorized"]


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
