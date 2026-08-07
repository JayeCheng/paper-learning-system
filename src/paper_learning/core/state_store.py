from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Iterable

from paper_learning.core.models import Paper, ReadingStatus
from paper_learning.core.normalize import normalize_paper
from paper_learning.utils.time import utc_now_string

STATE_VERSION = "0.3"
VALID_READING_STATUSES = {"backlog", "queued", "skimmed", "deep_read", "archived", "skipped"}
VALID_PRIORITIES = {"low", "medium", "high", "s_level"}


def state_dir(root: Path = Path(".")) -> Path:
    return root / "data" / "state"


def papers_path(root: Path = Path(".")) -> Path:
    return state_dir(root) / "papers.jsonl"


def reading_status_path(root: Path = Path(".")) -> Path:
    return state_dir(root) / "reading_status.json"


def run_history_path(root: Path = Path(".")) -> Path:
    return state_dir(root) / "run_history.json"


def load_papers(root: Path = Path(".")) -> list[Paper]:
    path = papers_path(root)
    if not path.exists():
        return []

    papers: list[Paper] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        papers.append(normalize_paper(json.loads(line)))
    return papers


def upsert_papers(papers: Iterable[Paper], *, root: Path = Path(".")) -> list[Paper]:
    paper_map = {paper.id: paper.to_dict() for paper in load_papers(root)}
    for paper in papers:
        existing = paper_map.get(paper.id, {})
        paper_map[paper.id] = _merge_paper(existing, paper.to_dict())

    merged = [normalize_paper(row) for row in paper_map.values()]
    write_papers(merged, root=root)
    return sorted(merged, key=lambda paper: paper.id)


def write_papers(papers: Iterable[Paper], *, root: Path = Path(".")) -> None:
    path = papers_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted((paper.to_dict() for paper in papers), key=lambda row: row["id"])
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def paper_exists(paper_id: str, *, root: Path = Path(".")) -> bool:
    return any(paper.id == paper_id for paper in load_papers(root))


def load_reading_statuses(root: Path = Path(".")) -> dict[str, ReadingStatus]:
    payload = _read_json(reading_status_path(root), default={})
    if not isinstance(payload, dict):
        return {}
    raw_items = payload.get("items", payload)
    statuses: dict[str, ReadingStatus] = {}
    if not isinstance(raw_items, dict):
        return statuses

    for paper_id, raw_value in raw_items.items():
        statuses[str(paper_id)] = _reading_status_from_raw(str(paper_id), raw_value)
    return statuses


def write_reading_statuses(statuses: dict[str, ReadingStatus], *, root: Path = Path(".")) -> None:
    path = reading_status_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    updated_at = _max_updated_at(statuses.values()) or utc_now_string()
    payload = {
        "state_version": STATE_VERSION,
        "updated_at": updated_at,
        "items": {paper_id: statuses[paper_id].to_dict() for paper_id in sorted(statuses)},
    }
    _write_json(path, payload)


def ensure_reading_status_entries(
    papers: Iterable[Paper],
    *,
    root: Path = Path("."),
    updated_at: str | None = None,
) -> dict[str, ReadingStatus]:
    statuses = load_reading_statuses(root)
    timestamp = updated_at or utc_now_string()
    changed = False

    for paper in papers:
        if paper.id in statuses:
            continue
        statuses[paper.id] = ReadingStatus(
            paper_id=paper.id,
            status="backlog",
            updated_at=timestamp,
            priority="s_level" if paper.selected_for_s_level else "medium",
            notes_path=None,
            history=[{"at": timestamp, "status": "backlog", "source": "daily_pipeline"}],
        )
        changed = True

    if changed:
        write_reading_statuses(statuses, root=root)
    return statuses


def set_reading_status(
    paper_id: str,
    *,
    root: Path = Path("."),
    status: str | None = None,
    priority: str | None = None,
    notes_path: str | None = None,
    updated_at: str | None = None,
) -> ReadingStatus:
    if not paper_exists(paper_id, root=root):
        raise ValueError(f"Paper '{paper_id}' does not exist in data/state/papers.jsonl.")
    if status is not None and status not in VALID_READING_STATUSES:
        raise ValueError(f"Invalid reading status '{status}'.")
    if priority is not None and priority not in VALID_PRIORITIES:
        raise ValueError(f"Invalid reading priority '{priority}'.")
    if status is None and priority is None and notes_path is None:
        raise ValueError("Set at least one of --status, --priority, or --notes-path.")

    statuses = load_reading_statuses(root)
    timestamp = updated_at or utc_now_string()
    current = statuses.get(
        paper_id,
        ReadingStatus(paper_id=paper_id, status="backlog", updated_at=timestamp),
    )
    new_status = status or current.status
    new_priority = priority or current.priority
    new_notes_path = notes_path if notes_path is not None else current.notes_path
    history = [
        *current.history,
        {
            "at": timestamp,
            "status": new_status,
            "priority": new_priority,
            "notes_path": new_notes_path,
            "source": "status_cli",
        },
    ]
    updated = replace(
        current,
        status=new_status,
        priority=new_priority,
        notes_path=new_notes_path,
        updated_at=timestamp,
        history=history,
    )
    statuses[paper_id] = updated
    write_reading_statuses(statuses, root=root)
    return updated


def load_run_history(root: Path = Path(".")) -> list[dict]:
    payload = _read_json(run_history_path(root), default={})
    if not isinstance(payload, dict):
        return []
    runs = payload.get("runs", [])
    return runs if isinstance(runs, list) else []


def append_run_history(
    *,
    root: Path = Path("."),
    date: str,
    generated_at: str,
    generated_paths: dict[str, str],
    paper_count: int,
    s_level_paper_id: str | None,
    status: str = "success",
) -> list[dict]:
    path = run_history_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    runs = load_run_history(root)
    runs.append(
        {
            "date": date,
            "generated_at": generated_at,
            "generated_paths": generated_paths,
            "paper_count": paper_count,
            "s_level_paper_id": s_level_paper_id,
            "status": status,
        }
    )
    payload = {"state_version": STATE_VERSION, "updated_at": generated_at, "runs": runs}
    _write_json(path, payload)
    return runs


def apply_reading_statuses(papers: Iterable[Paper], statuses: dict[str, ReadingStatus]) -> list[Paper]:
    updated: list[Paper] = []
    for paper in papers:
        status = statuses.get(paper.id)
        updated.append(replace(paper, reading_status=status.status) if status else paper)
    return updated


def _merge_paper(existing: dict, new: dict) -> dict:
    merged = dict(existing)
    for key, value in new.items():
        if value in (None, "", [], {}):
            continue
        merged[key] = value
    if "id" not in merged:
        merged["id"] = new["id"]
    return merged


def _reading_status_from_raw(paper_id: str, raw_value: object) -> ReadingStatus:
    if isinstance(raw_value, str):
        return ReadingStatus(paper_id=paper_id, status=raw_value, updated_at="")
    if not isinstance(raw_value, dict):
        return ReadingStatus(paper_id=paper_id, status="backlog", updated_at="")

    return ReadingStatus(
        paper_id=str(raw_value.get("paper_id") or paper_id),
        status=str(raw_value.get("status") or "backlog"),
        updated_at=str(raw_value.get("updated_at") or ""),
        priority=str(raw_value.get("priority") or "medium"),
        notes_path=raw_value.get("notes_path"),
        history=list(raw_value.get("history") or []),
    )


def _max_updated_at(statuses: Iterable[ReadingStatus]) -> str | None:
    timestamps = [status.updated_at for status in statuses if status.updated_at]
    return max(timestamps) if timestamps else None


def _read_json(path: Path, *, default: object) -> object:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
