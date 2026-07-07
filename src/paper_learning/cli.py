from __future__ import annotations

import argparse
from pathlib import Path

from paper_learning.reports.daily_report import build_daily_report, write_daily_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="paper-learning")
    subparsers = parser.add_subparsers(dest="command")

    daily = subparsers.add_parser("daily", help="Generate a placeholder daily report.")
    daily.add_argument("--date", help="Report date in YYYY-MM-DD format.")
    daily.add_argument("--markdown-output", type=Path, help="Optional Markdown output path.")
    daily.add_argument("--json-output", type=Path, help="Optional JSON output path.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command in (None, "daily"):
        report = build_daily_report(date=args.date)
        markdown_path, json_path = write_daily_report(
            report,
            markdown_path=args.markdown_output,
            json_path=args.json_output,
        )
        print(f"Wrote {markdown_path}")
        print(f"Wrote {json_path}")
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
