import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from paper_learning.core.models import DailyReport, NoteIndexEntry, Paper
from paper_learning.reports.public_json import write_public_json


def _note(note_id: str, note_type: str, url: str, updated_at: str) -> NoteIndexEntry:
    return NoteIndexEntry(
        note_id=note_id,
        paper_id="p1",
        note_type=note_type,
        title=f"Note {note_id}",
        notion_url=url,
        local_markdown_path=None,
        status="published",
        created_at="2026-07-27T09:00:00+00:00",
        updated_at=updated_at,
        tags=["bridge"],
        linked_knowledge_nodes=["notion-bridge"],
    )


def test_public_notes_index_and_paper_note_summary(tmp_path) -> None:
    paper = Paper(
        id="p1",
        title="Public Note Paper",
        source="manual",
        topics=["llm_agent"],
        url="https://example.com/p1",
    )
    notes = [
        _note(
            "note:deep",
            "deep_read",
            "https://www.notion.so/deep",
            "2026-07-27T10:00:00+00:00",
        ),
        _note(
            "note:method",
            "method_card",
            "https://www.notion.so/method",
            "2026-07-27T11:00:00+00:00",
        ),
    ]
    report = DailyReport(
        date="2026-07-27",
        generated_at="2026-07-27T12:00:00+00:00",
        summary="Notes bridge",
        papers=[paper],
    )

    write_public_json(
        report=report,
        papers=[paper],
        reading_statuses={},
        run_history=[],
        public_dir=tmp_path,
        notes=notes,
    )

    notes_payload = json.loads((tmp_path / "notes_index.json").read_text(encoding="utf-8"))
    papers_payload = json.loads((tmp_path / "papers_index.json").read_text(encoding="utf-8"))

    assert notes_payload["public_json_version"] == "0.4"
    assert len(notes_payload["notes"]) == 2
    assert papers_payload["papers"][0]["note_count"] == 2
    assert papers_payload["papers"][0]["latest_note_url"] == "https://www.notion.so/method"
    assert papers_payload["papers"][0]["deep_read_note_url"] == "https://www.notion.so/deep"

    schema = json.loads(Path("schemas/notes_index.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(notes_payload)


def test_empty_public_notes_index_is_frontend_safe(tmp_path) -> None:
    report = DailyReport(
        date="2026-07-27",
        generated_at="2026-07-27T12:00:00+00:00",
        summary="No notes",
    )
    write_public_json(
        report=report,
        papers=[],
        reading_statuses={},
        run_history=[],
        public_dir=tmp_path,
        notes=[],
    )

    payload = json.loads((tmp_path / "notes_index.json").read_text(encoding="utf-8"))

    assert payload == {
        "notes": [],
        "public_json_version": "0.4",
        "updated_at": "2026-07-27T12:00:00+00:00",
    }
