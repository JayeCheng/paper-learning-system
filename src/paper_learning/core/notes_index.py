from __future__ import annotations

from dataclasses import replace
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Iterable
from urllib.parse import urlparse

from paper_learning.core.models import NoteIndexEntry, Paper
from paper_learning.core.state_store import paper_exists
from paper_learning.utils.config import slugify
from paper_learning.utils.time import utc_now_string

NOTES_STATE_VERSION = "0.4"
NOTE_TYPES = {
    "deep_read",
    "concept_card",
    "method_card",
    "english_card",
    "project_note",
}
NOTE_STATUSES = {"planned", "drafting", "published", "archived"}
_UNSET = object()


def notes_index_path(root: Path = Path(".")) -> Path:
    return root / "data" / "state" / "notes_index.json"


def load_notes(root: Path = Path(".")) -> list[NoteIndexEntry]:
    path = notes_index_path(root)
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_notes = payload.get("notes", []) if isinstance(payload, dict) else []
    if not isinstance(raw_notes, list):
        raise ValueError(f"{path} must contain a notes array")
    return [_note_from_raw(raw, root=root) for raw in raw_notes if isinstance(raw, dict)]


def write_notes(notes: Iterable[NoteIndexEntry], *, root: Path = Path(".")) -> None:
    path = notes_index_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    validated = [_validated_note(note, root=root) for note in notes]
    ordered = sorted(validated, key=lambda note: (note.created_at, note.note_id))
    updated_at = max((note.updated_at for note in ordered), default=None)
    payload = {
        "state_version": NOTES_STATE_VERSION,
        "updated_at": updated_at,
        "notes": [note.to_dict() for note in ordered],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def add_note(
    *,
    paper_id: str,
    note_type: str,
    title: str,
    notion_url: str | None = None,
    local_markdown_path: str | None = None,
    status: str = "planned",
    tags: list[str] | None = None,
    root: Path = Path("."),
    timestamp: str | None = None,
) -> NoteIndexEntry:
    _validate_note_type(note_type)
    _validate_status(status)
    if not paper_exists(paper_id, root=root):
        raise ValueError(f"Paper '{paper_id}' does not exist in data/state/papers.jsonl.")
    if not title.strip():
        raise ValueError("Note title must not be empty.")
    validated_url, validated_path = _validate_note_locations(
        notion_url,
        local_markdown_path,
        root=root,
    )

    notes = load_notes(root)
    note_id = _note_id(paper_id, note_type, title)
    if any(note.note_id == note_id for note in notes):
        raise ValueError(f"Note '{note_id}' already exists.")
    now = timestamp or utc_now_string()
    note = NoteIndexEntry(
        note_id=note_id,
        paper_id=paper_id,
        note_type=note_type,
        title=title.strip(),
        notion_url=validated_url,
        local_markdown_path=validated_path,
        status=status,
        created_at=now,
        updated_at=now,
        tags=_unique_values(tags or []),
        linked_knowledge_nodes=[],
    )
    write_notes([*notes, note], root=root)
    return note


def update_note(
    note_id: str,
    *,
    status: str | None = None,
    notion_url: str | None | object = _UNSET,
    local_markdown_path: str | None | object = _UNSET,
    root: Path = Path("."),
    timestamp: str | None = None,
) -> NoteIndexEntry:
    if status is None and notion_url is _UNSET and local_markdown_path is _UNSET:
        raise ValueError("Provide at least one field to update.")
    if status is not None:
        _validate_status(status)
    notes = load_notes(root)
    current = _find_note(notes, note_id)
    next_url = current.notion_url if notion_url is _UNSET else _optional_text(notion_url)
    next_path = (
        current.local_markdown_path
        if local_markdown_path is _UNSET
        else _optional_text(local_markdown_path)
    )
    validated_url, validated_path = _validate_note_locations(next_url, next_path, root=root)
    updated = replace(
        current,
        status=status or current.status,
        notion_url=validated_url,
        local_markdown_path=validated_path,
        updated_at=timestamp or utc_now_string(),
    )
    write_notes([updated if note.note_id == note_id else note for note in notes], root=root)
    return updated


def link_knowledge_node(
    note_id: str,
    *,
    knowledge_node: str,
    root: Path = Path("."),
    timestamp: str | None = None,
) -> NoteIndexEntry:
    node = knowledge_node.strip()
    if not node:
        raise ValueError("Knowledge node must not be empty.")
    notes = load_notes(root)
    current = _find_note(notes, note_id)
    linked = _unique_values([*current.linked_knowledge_nodes, node])
    updated = replace(
        current,
        linked_knowledge_nodes=linked,
        updated_at=timestamp or utc_now_string(),
    )
    write_notes([updated if note.note_id == note_id else note for note in notes], root=root)
    return updated


def annotate_report_papers(
    papers: list[Paper],
    notes: list[NoteIndexEntry],
) -> list[Paper]:
    notes_by_paper = _notes_by_paper(notes)
    annotated: list[Paper] = []
    for paper in papers:
        if not paper.selected_for_s_level:
            annotated.append(paper)
            continue
        paper_notes = notes_by_paper.get(paper.id, [])
        annotated.append(
            replace(
                paper,
                existing_note_url=_latest_notion_url(paper_notes),
                suggested_note_type="deep_read",
                suggested_note_title=f"Deep Read: {paper.title}",
            )
        )
    return annotated


def note_metadata_for_paper(
    paper_id: str,
    notes: list[NoteIndexEntry],
) -> dict[str, object]:
    paper_notes = _notes_by_paper(notes).get(paper_id, [])
    deep_read_notes = [note for note in paper_notes if note.note_type == "deep_read"]
    return {
        "note_count": len(paper_notes),
        "latest_note_url": _latest_notion_url(paper_notes),
        "deep_read_note_url": _latest_notion_url(deep_read_notes),
    }


def _note_from_raw(raw: dict, *, root: Path) -> NoteIndexEntry:
    note_type = str(raw.get("note_type") or "")
    status = str(raw.get("status") or "")
    _validate_note_type(note_type)
    _validate_status(status)
    notion_url, local_markdown_path = _validate_note_locations(
        raw.get("notion_url"),
        raw.get("local_markdown_path"),
        root=root,
    )
    note = NoteIndexEntry(
        note_id=str(raw.get("note_id") or ""),
        paper_id=str(raw.get("paper_id") or ""),
        note_type=note_type,
        title=str(raw.get("title") or ""),
        notion_url=notion_url,
        local_markdown_path=local_markdown_path,
        status=status,
        created_at=str(raw.get("created_at") or ""),
        updated_at=str(raw.get("updated_at") or ""),
        tags=_unique_values(list(raw.get("tags") or [])),
        linked_knowledge_nodes=_unique_values(list(raw.get("linked_knowledge_nodes") or [])),
    )
    return _validated_note(note, root=root)


def _note_id(paper_id: str, note_type: str, title: str) -> str:
    identity = f"{paper_id}\0{note_type}\0{title.strip()}".encode("utf-8")
    suffix = hashlib.sha1(identity).hexdigest()[:8]
    return f"note:{note_type}:{slugify(title)}-{suffix}"


def _find_note(notes: list[NoteIndexEntry], note_id: str) -> NoteIndexEntry:
    for note in notes:
        if note.note_id == note_id:
            return note
    raise ValueError(f"Note '{note_id}' does not exist.")


def _notes_by_paper(notes: list[NoteIndexEntry]) -> dict[str, list[NoteIndexEntry]]:
    grouped: dict[str, list[NoteIndexEntry]] = {}
    for note in notes:
        grouped.setdefault(note.paper_id, []).append(note)
    for paper_notes in grouped.values():
        paper_notes.sort(key=lambda note: (note.updated_at, note.note_id), reverse=True)
    return grouped


def _latest_notion_url(notes: list[NoteIndexEntry]) -> str | None:
    return next((note.notion_url for note in notes if note.notion_url), None)


def _validate_note_type(value: str) -> None:
    if value not in NOTE_TYPES:
        raise ValueError(f"Invalid note type '{value}'.")


def _validate_status(value: str) -> None:
    if value not in NOTE_STATUSES:
        raise ValueError(f"Invalid note status '{value}'.")


def _unique_values(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))


def _optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _validated_note(note: NoteIndexEntry, *, root: Path) -> NoteIndexEntry:
    if not note.note_id.strip():
        raise ValueError("Note id must not be empty.")
    if not note.paper_id.strip():
        raise ValueError("Paper id must not be empty.")
    if not note.title.strip():
        raise ValueError("Note title must not be empty.")
    _validate_note_type(note.note_type)
    _validate_status(note.status)
    _validate_timestamp(note.created_at, field_name="created_at")
    _validate_timestamp(note.updated_at, field_name="updated_at")
    notion_url, local_markdown_path = _validate_note_locations(
        note.notion_url,
        note.local_markdown_path,
        root=root,
    )
    return replace(
        note,
        note_id=note.note_id.strip(),
        paper_id=note.paper_id.strip(),
        title=note.title.strip(),
        notion_url=notion_url,
        local_markdown_path=local_markdown_path,
    )


def _validate_note_locations(
    notion_url: object,
    local_markdown_path: object,
    *,
    root: Path,
) -> tuple[str | None, str | None]:
    normalized_url = _optional_text(notion_url)
    normalized_path = _optional_text(local_markdown_path)
    if normalized_url is None and normalized_path is None:
        raise ValueError("Provide --notion-url or --local-markdown-path.")
    if normalized_url is not None:
        _validate_http_url(normalized_url)
    if normalized_path is not None:
        normalized_path = _validate_local_markdown_path(normalized_path, root=root)
    return normalized_url, normalized_path


def _validate_http_url(value: str) -> None:
    if any(character.isspace() for character in value):
        raise ValueError("Notion URL must be an absolute HTTP(S) URL.")
    parsed = urlparse(value)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Notion URL must be an absolute HTTP(S) URL.") from exc
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.netloc
        or not parsed.hostname
        or (port is not None and not 1 <= port <= 65535)
    ):
        raise ValueError("Notion URL must be an absolute HTTP(S) URL.")


def _validate_local_markdown_path(value: str, *, root: Path) -> str:
    windows_path = PureWindowsPath(value)
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        windows_path.is_absolute()
        or bool(windows_path.drive)
        or path.is_absolute()
        or ".." in path.parts
        or not path.parts
        or path.suffix.lower() != ".md"
    ):
        raise ValueError(
            "Local Markdown path must be a repository-relative .md path without '..'."
        )

    repository_root = root.resolve()
    candidate = (repository_root / Path(*path.parts)).resolve()
    try:
        candidate.relative_to(repository_root)
    except ValueError as exc:
        raise ValueError("Local Markdown path must stay inside the repository.") from exc
    return path.as_posix()


def _validate_timestamp(value: str, *, field_name: str) -> None:
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Note {field_name} must be an ISO 8601 date-time.") from exc
    if timestamp.tzinfo is None:
        raise ValueError(f"Note {field_name} must include a timezone.")
