from __future__ import annotations

import argparse
import sys
from pathlib import Path

from paper_learning.core.daily_pipeline import run_daily_pipeline
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

    papers = load_papers(root)
    statuses = load_reading_statuses(root)
    run_history = load_run_history(root)
    write_exports(papers=papers, reading_statuses=statuses, exports_dir=root / "data" / "exports")
    write_public_json(
        report=None,
        papers=papers,
        reading_statuses=statuses,
        run_history=run_history,
        public_dir=root / "data" / "public",
    )
    print(f"Updated {updated.paper_id}: status={updated.status} priority={updated.priority}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
