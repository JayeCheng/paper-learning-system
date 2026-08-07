import json
import os
from pathlib import Path

import pytest

from paper_learning.cli import main
from paper_learning.core.models import Paper
from paper_learning.core.state_store import upsert_papers


def _paper() -> Paper:
    return Paper(
        id="arxiv:2607.00002",
        title="CLI Note Paper",
        source="arxiv",
        topics=["llm_agent"],
        url="https://example.com/cli-note",
    )


def test_note_cli_add_update_link_and_list(tmp_path, capsys) -> None:
    previous = Path.cwd()
    os.chdir(tmp_path)
    try:
        upsert_papers([_paper()])
        assert (
            main(
                [
                    "note",
                    "add",
                    "--paper-id",
                    _paper().id,
                    "--type",
                    "deep_read",
                    "--title",
                    "Deep Read CLI Note",
                    "--notion-url",
                    "https://www.notion.so/cli-note",
                    "--tag",
                    "cli",
                ]
            )
            == 0
        )
        state = json.loads(Path("data/state/notes_index.json").read_text(encoding="utf-8"))
        note_id = state["notes"][0]["note_id"]

        assert main(["note", "update", note_id, "--status", "published"]) == 0
        assert (
            main(
                [
                    "note",
                    "link",
                    "--note-id",
                    note_id,
                    "--knowledge-node",
                    "cli-note-node",
                ]
            )
            == 0
        )
        assert main(["note", "list"]) == 0

        output = capsys.readouterr().out
        state = json.loads(Path("data/state/notes_index.json").read_text(encoding="utf-8"))
        public = json.loads(Path("data/public/notes_index.json").read_text(encoding="utf-8"))
        csv_text = Path("data/exports/notes_index.csv").read_text(encoding="utf-8")

        assert note_id in output
        assert state["notes"][0]["status"] == "published"
        assert state["notes"][0]["linked_knowledge_nodes"] == ["cli-note-node"]
        assert public["notes"][0]["notion_url"] == "https://www.notion.so/cli-note"
        assert "Deep Read CLI Note" in csv_text
    finally:
        os.chdir(previous)


def test_note_cli_errors_for_unknown_note(tmp_path) -> None:
    previous = Path.cwd()
    os.chdir(tmp_path)
    try:
        assert main(["note", "update", "missing", "--status", "published"]) == 1
    finally:
        os.chdir(previous)


def test_note_cli_adds_local_only_note(tmp_path) -> None:
    previous = Path.cwd()
    os.chdir(tmp_path)
    try:
        upsert_papers([_paper()])

        assert (
            main(
                [
                    "note",
                    "add",
                    "--paper-id",
                    _paper().id,
                    "--type",
                    "project_note",
                    "--title",
                    "Local Only",
                    "--local-markdown-path",
                    "deep_read/local-only.md",
                ]
            )
            == 0
        )

        note = json.loads(Path("data/state/notes_index.json").read_text())["notes"][0]
        assert note["notion_url"] is None
        assert note["local_markdown_path"] == "deep_read/local-only.md"
    finally:
        os.chdir(previous)


@pytest.mark.parametrize(
    "location_args",
    [
        [],
        ["--notion-url", "notion://not-absolute-http"],
        ["--local-markdown-path", "/tmp/outside.md"],
        ["--local-markdown-path", "../outside.md"],
    ],
)
def test_note_cli_rejects_invalid_or_missing_locations(tmp_path, location_args) -> None:
    previous = Path.cwd()
    os.chdir(tmp_path)
    try:
        upsert_papers([_paper()])
        args = [
            "note",
            "add",
            "--paper-id",
            _paper().id,
            "--type",
            "deep_read",
            "--title",
            "Invalid Location",
            *location_args,
        ]

        assert main(args) == 1
        assert not Path("data/state/notes_index.json").exists()
    finally:
        os.chdir(previous)


def test_note_cli_update_repairs_url_and_local_path(tmp_path) -> None:
    previous = Path.cwd()
    os.chdir(tmp_path)
    try:
        upsert_papers([_paper()])
        assert (
            main(
                [
                    "note",
                    "add",
                    "--paper-id",
                    _paper().id,
                    "--type",
                    "method_card",
                    "--title",
                    "Repair Locations",
                    "--notion-url",
                    "https://www.notion.so/original",
                ]
            )
            == 0
        )
        note_id = json.loads(Path("data/state/notes_index.json").read_text())["notes"][0][
            "note_id"
        ]

        assert (
            main(
                [
                    "note",
                    "update",
                    note_id,
                    "--status",
                    "published",
                    "--notion-url",
                    "https://app.notion.com/p/repaired",
                    "--local-markdown-path",
                    "deep_read/repaired.md",
                ]
            )
            == 0
        )

        note = json.loads(Path("data/state/notes_index.json").read_text())["notes"][0]
        assert note["status"] == "published"
        assert note["notion_url"] == "https://app.notion.com/p/repaired"
        assert note["local_markdown_path"] == "deep_read/repaired.md"
    finally:
        os.chdir(previous)
