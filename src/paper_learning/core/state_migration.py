from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import urlparse

from paper_learning.core.normalize import CATEGORY_TOPIC_MAP, normalize_paper
from paper_learning.core.notes_index import load_notes
from paper_learning.core.state_store import (
    load_reading_statuses,
    load_run_history,
    papers_path,
)
from paper_learning.reports.exports import write_exports
from paper_learning.reports.public_json import write_public_json


@dataclass(frozen=True)
class MigrationChange:
    paper_id: str
    fields: tuple[str, ...]


@dataclass(frozen=True)
class MigrationResult:
    changed_papers: int
    changes: tuple[MigrationChange, ...]
    dry_run: bool


def migrate_v03_state(*, root: Path, dry_run: bool = False) -> MigrationResult:
    """Apply the one-time v0.3.1 cleanup without using normal upsert semantics."""

    path = papers_path(root)
    rows = _read_jsonl_rows(path)
    migrated: list[dict] = []
    changes: list[MigrationChange] = []
    for row in rows:
        updated, fields = _migrate_row(row)
        migrated.append(updated)
        if fields:
            changes.append(MigrationChange(str(row.get("id") or ""), tuple(fields)))

    result = MigrationResult(len(changes), tuple(changes), dry_run)
    if dry_run or not changes:
        return result

    _atomic_write_jsonl(path, migrated)
    _regenerate_derived_outputs(root)
    return result


def _read_jsonl_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number} must contain a JSON object")
        rows.append(value)
    return rows


def _migrate_row(row: dict) -> tuple[dict, list[str]]:
    updated = dict(row)
    fields: list[str] = []

    code_url = updated.get("code_url")
    if isinstance(code_url, str) and _is_curriculum_repository_url(code_url):
        updated["code_url"] = None
        fields.append("code_url")

    current_topics = list(updated.get("topics") or [])
    if not current_topics or set(current_topics) <= {"uncategorized"}:
        inferred = _infer_topics(updated)
        if inferred and inferred != current_topics:
            updated["topics"] = inferred
            fields.append("topics")
    return updated, fields


def _is_curriculum_repository_url(value: str) -> bool:
    parsed = urlparse(value)
    return (
        parsed.netloc.lower() in {"github.com", "www.github.com"}
        and parsed.path.lower().startswith(
            "/jayecheng/paper-learning-system/blob/main/curriculum/"
        )
    )


def _infer_topics(row: dict) -> list[str]:
    topics: list[str] = []
    values = [
        *(row.get("categories") or []),
        *(row.get("tags") or []),
        row.get("field"),
        row.get("source_group"),
    ]
    lower_map = {key.casefold(): value for key, value in CATEGORY_TOPIC_MAP.items()}
    for raw in values:
        if not raw:
            continue
        value = str(raw)
        topic = CATEGORY_TOPIC_MAP.get(value) or lower_map.get(value.casefold())
        if topic and topic not in topics:
            topics.append(topic)
    return topics


def _atomic_write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            for row in rows:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    except (OSError, TypeError, ValueError):
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def _regenerate_derived_outputs(root: Path) -> None:
    papers = [normalize_paper(row) for row in _read_jsonl_rows(papers_path(root))]
    statuses = load_reading_statuses(root)
    run_history = load_run_history(root)
    notes = load_notes(root)
    daily_papers = _load_latest_daily_papers(root, run_history)
    write_exports(
        papers=papers,
        reading_statuses=statuses,
        daily_papers=daily_papers,
        exports_dir=root / "data" / "exports",
        notes=notes,
    )
    write_public_json(
        report=None,
        papers=papers,
        reading_statuses=statuses,
        run_history=run_history,
        public_dir=root / "data" / "public",
        notes=notes,
    )


def _load_latest_daily_papers(root: Path, run_history: list[dict]) -> list:
    for run in reversed(run_history):
        raw_path = dict(run.get("generated_paths") or {}).get("json")
        if run.get("status") != "success" or not raw_path:
            continue
        path = root / str(raw_path)
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        return [
            normalize_paper(_migrate_row(raw)[0])
            for raw in payload.get("papers") or []
            if isinstance(raw, dict)
        ]
    return []
