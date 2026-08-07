from __future__ import annotations

import argparse
import sys
from pathlib import Path

from paper_learning.core.daily_pipeline import run_daily_pipeline
from paper_learning.core.notes_index import (
    NOTE_STATUSES,
    NOTE_TYPES,
    add_note,
    link_knowledge_node,
    load_notes,
    update_note,
)
from paper_learning.core.state_store import (
    load_papers,
    load_reading_statuses,
    load_run_history,
    set_reading_status,
)
from paper_learning.reports.exports import write_exports
from paper_learning.reports.public_json import write_public_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="paper-learning")
    subparsers = parser.add_subparsers(dest="command")

    daily = subparsers.add_parser("daily", help="Run the daily paper radar.")
    daily.add_argument("--date", default="today", help="Report date: today or YYYY-MM-DD.")

    status = subparsers.add_parser("status", help="Inspect or update reading status.")
    status_subparsers = status.add_subparsers(dest="status_command")
    status_subparsers.add_parser("list", help="List durable reading statuses.")
    status_set = status_subparsers.add_parser("set", help="Update one paper's reading status.")
    status_set.add_argument("paper_id", help="Paper id from data/state/papers.jsonl.")
    status_set.add_argument(
        "--status",
        choices=["backlog", "queued", "skimmed", "deep_read", "archived", "skipped"],
        help="Long-term reading state.",
    )
    status_set.add_argument(
        "--priority",
        choices=["low", "medium", "high", "s_level"],
        help="Reading priority.",
    )
    status_set.add_argument("--notes-path", help="Path or URL for durable notes.")

    note = subparsers.add_parser("note", help="Manage durable Notion bridge metadata.")
    note_subparsers = note.add_subparsers(dest="note_command")
    note_subparsers.add_parser("list", help="List note metadata from GitHub state.")

    note_add = note_subparsers.add_parser("add", help="Add a manual note metadata entry.")
    note_add.add_argument("--paper-id", required=True)
    note_add.add_argument("--type", required=True, choices=sorted(NOTE_TYPES), dest="note_type")
    note_add.add_argument("--title", required=True)
    note_add.add_argument("--notion-url", help="Optional absolute HTTP(S) Notion URL.")
    note_add.add_argument(
        "--local-markdown-path",
        help="Optional repository-relative Markdown path; one note location is required.",
    )
    note_add.add_argument("--status", choices=sorted(NOTE_STATUSES), default="planned")
    note_add.add_argument("--tag", action="append", default=[], dest="tags")

    note_update = note_subparsers.add_parser("update", help="Update note metadata.")
    note_update.add_argument("note_id")
    note_update.add_argument(
        "--status",
        choices=sorted(NOTE_STATUSES),
        default=argparse.SUPPRESS,
    )
    note_update.add_argument("--notion-url", default=argparse.SUPPRESS)
    note_update.add_argument("--local-markdown-path", default=argparse.SUPPRESS)

    note_link = note_subparsers.add_parser("link", help="Link a note to a knowledge node.")
    note_link.add_argument("--note-id", required=True)
    note_link.add_argument("--knowledge-node", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command in (None, "daily"):
        _report, markdown_path, json_path = run_daily_pipeline(getattr(args, "date", "today"))
        print(f"Wrote {markdown_path}")
        print(f"Wrote {json_path}")
        return 0

    if args.command == "status":
        if args.status_command == "list":
            return _status_list()
        if args.status_command == "set":
            return _status_set(args)
        parser.error("status requires a subcommand: list or set")
        return 2

    if args.command == "note":
        if args.note_command == "list":
            return _note_list()
        if args.note_command == "add":
            return _note_add(args)
        if args.note_command == "update":
            return _note_update(args)
        if args.note_command == "link":
            return _note_link(args)
        parser.error("note requires a subcommand: list, add, update, or link")
        return 2

    parser.error(f"Unknown command: {args.command}")
    return 2


def _status_list(root: Path = Path(".")) -> int:
    papers = {paper.id: paper for paper in load_papers(root)}
    statuses = load_reading_statuses(root)
    if not statuses:
        print("No reading statuses found.")
        return 0

    for paper_id in sorted(statuses):
        status = statuses[paper_id]
        paper = papers.get(paper_id)
        title = paper.title if paper else "(paper metadata missing)"
        print(f"{paper_id}\t{status.status}\t{status.priority}\t{status.notes_path or ''}\t{title}")
    return 0


def _status_set(args: argparse.Namespace, root: Path = Path(".")) -> int:
    try:
        updated = set_reading_status(
            args.paper_id,
            root=root,
            status=args.status,
            priority=args.priority,
            notes_path=args.notes_path,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    _refresh_derived_views(root)
    print(f"Updated {updated.paper_id}: status={updated.status} priority={updated.priority}")
    return 0


def _note_list(root: Path = Path(".")) -> int:
    notes = load_notes(root)
    if not notes:
        print("No notes found.")
        return 0
    for note in sorted(notes, key=lambda item: (item.updated_at, item.note_id), reverse=True):
        location = note.notion_url or note.local_markdown_path or ""
        print(
            f"{note.note_id}\t{note.paper_id}\t{note.note_type}\t"
            f"{note.status}\t{location}\t{note.title}"
        )
    return 0


def _note_add(args: argparse.Namespace, root: Path = Path(".")) -> int:
    try:
        note = add_note(
            paper_id=args.paper_id,
            note_type=args.note_type,
            title=args.title,
            notion_url=args.notion_url,
            local_markdown_path=args.local_markdown_path,
            status=args.status,
            tags=args.tags,
            root=root,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    _refresh_derived_views(root)
    print(f"Added {note.note_id}: {note.title}")
    return 0


def _note_update(args: argparse.Namespace, root: Path = Path(".")) -> int:
    updates = {
        name: getattr(args, name)
        for name in ("status", "notion_url", "local_markdown_path")
        if hasattr(args, name)
    }
    try:
        note = update_note(args.note_id, root=root, **updates)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    _refresh_derived_views(root)
    print(f"Updated {note.note_id}: status={note.status}")
    return 0


def _note_link(args: argparse.Namespace, root: Path = Path(".")) -> int:
    try:
        note = link_knowledge_node(
            args.note_id,
            knowledge_node=args.knowledge_node,
            root=root,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    _refresh_derived_views(root)
    print(f"Linked {note.note_id}: {args.knowledge_node}")
    return 0


def _refresh_derived_views(root: Path) -> None:
    papers = load_papers(root)
    statuses = load_reading_statuses(root)
    run_history = load_run_history(root)
    notes = load_notes(root)
    write_exports(
        papers=papers,
        reading_statuses=statuses,
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


if __name__ == "__main__":
    raise SystemExit(main())
