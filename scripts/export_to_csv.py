from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from paper_learning.core.state_store import load_papers, load_reading_statuses
from paper_learning.reports.exports import write_exports


def main() -> int:
    paths = write_exports(
        papers=load_papers(ROOT),
        reading_statuses=load_reading_statuses(ROOT),
        exports_dir=ROOT / "data" / "exports",
    )
    for path in paths.values():
        print(f"Wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
