from __future__ import annotations

import argparse
from pathlib import Path

from paper_learning.core.state_migration import migrate_v03_state


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate durable v0.3 state to v0.3.1.")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = migrate_v03_state(root=args.root, dry_run=args.dry_run)
    mode = "DRY RUN" if result.dry_run else "MIGRATED"
    verb = "would change" if result.dry_run else "changed"
    print(f"{mode}: {result.changed_papers} paper(s) {verb}.")
    for change in result.changes:
        print(f"- {change.paper_id}: {', '.join(change.fields)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
