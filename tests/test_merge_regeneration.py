import csv
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from paper_learning.core.models import NoteIndexEntry
from paper_learning.core.notes_index import write_notes
from paper_learning.core.state_migration import _regenerate_derived_outputs


def _write_merged_durable_state(root: Path) -> tuple[Path, Path, Path]:
    state_dir = root / "data/state"
    daily_path = root / "daily/2026/08/2026-08-01.json"
    state_dir.mkdir(parents=True)
    daily_path.parent.mkdir(parents=True)
    paper = {
        "id": "arxiv:2608.00001v1",
        "title": "Merged Main Paper",
        "source": "arxiv",
        "source_type": "recent_24h",
        "source_group": "llm_agent",
        "topics": ["llm_agent"],
        "url": "https://arxiv.org/abs/2608.00001v1",
        "published_date": "2026-08-01",
    }
    papers_path = state_dir / "papers.jsonl"
    papers_path.write_text(json.dumps(paper) + "\n", encoding="utf-8")
    reading_path = state_dir / "reading_status.json"
    reading_path.write_text(
        json.dumps(
            {
                "state_version": "0.3",
                "updated_at": "2026-08-01T22:10:00+00:00",
                "items": {
                    paper["id"]: {
                        "paper_id": paper["id"],
                        "status": "backlog",
                        "priority": "medium",
                        "notes_path": None,
                        "updated_at": "2026-08-01T22:10:00+00:00",
                        "history": [],
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    history_path = state_dir / "run_history.json"
    history_path.write_text(
        json.dumps(
            {
                "state_version": "0.3",
                "updated_at": "2026-08-01T22:10:00+00:00",
                "runs": [
                    {
                        "date": "2026-08-01",
                        "generated_at": "2026-08-01T22:10:00+00:00",
                        "generated_paths": {
                            "json": "daily/2026/08/2026-08-01.json",
                            "markdown": "daily/2026/08/2026-08-01.md",
                        },
                        "paper_count": 1,
                        "s_level_paper_id": None,
                        "status": "success",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    daily_path.write_text(
        json.dumps(
            {
                "date": "2026-08-01",
                "generated_at": "2026-08-01T22:10:00+00:00",
                "summary": "Latest main report",
                "papers": [paper],
            }
        ),
        encoding="utf-8",
    )
    write_notes(
        [
            NoteIndexEntry(
                note_id="note:project_note:merged",
                paper_id=paper["id"],
                note_type="project_note",
                title="Merged v0.4 note",
                notion_url=None,
                local_markdown_path="deep_read/merged-note.md",
                status="published",
                created_at="2026-08-01T20:00:00+00:00",
                updated_at="2026-08-01T20:00:00+00:00",
                tags=["merge"],
                linked_knowledge_nodes=[],
            )
        ],
        root=root,
    )
    return papers_path, reading_path, history_path


def test_main_daily_state_and_v04_notes_survive_idempotent_regeneration(tmp_path) -> None:
    durable_paths = _write_merged_durable_state(tmp_path)
    notes_path = tmp_path / "data/state/notes_index.json"
    daily_path = tmp_path / "daily/2026/08/2026-08-01.json"
    durable_before = {
        path: path.read_bytes() for path in (*durable_paths, notes_path, daily_path)
    }

    _regenerate_derived_outputs(tmp_path)

    assert {path: path.read_bytes() for path in durable_before} == durable_before
    latest = json.loads((tmp_path / "data/public/latest.json").read_text())
    public_notes = json.loads((tmp_path / "data/public/notes_index.json").read_text())
    public_papers = json.loads((tmp_path / "data/public/papers_index.json").read_text())
    assert latest["latest"]["date"] == "2026-08-01"
    assert public_notes["notes"][0]["local_markdown_path"] == "deep_read/merged-note.md"
    assert public_papers["papers"][0]["note_count"] == 1
    with (tmp_path / "data/exports/notes_index.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["note_id"] == "note:project_note:merged"

    schema = json.loads(Path("schemas/notes_index.schema.json").read_text())
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    validator.validate(json.loads(notes_path.read_text()))
    validator.validate(public_notes)

    derived_paths = sorted((tmp_path / "data/public").glob("*.json"))
    derived_paths.extend(sorted((tmp_path / "data/exports").glob("*")))
    first_generation = {path: path.read_bytes() for path in derived_paths}
    _regenerate_derived_outputs(tmp_path)
    assert {path: path.read_bytes() for path in derived_paths} == first_generation
