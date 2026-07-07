from __future__ import annotations

import argparse

from paper_learning.core.daily_pipeline import run_daily_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="paper-learning")
    subparsers = parser.add_subparsers(dest="command")

    daily = subparsers.add_parser("daily", help="Run the daily paper radar.")
    daily.add_argument("--date", default="today", help="Report date: today or YYYY-MM-DD.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command in (None, "daily"):
        _report, markdown_path, json_path = run_daily_pipeline(getattr(args, "date", "today"))
        print(f"Wrote {markdown_path}")
        print(f"Wrote {json_path}")
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
