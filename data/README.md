# Data Directory

This directory stores repository-owned data.

- `state/` is durable internal state that automation may update through pull requests.
- `raw/` stores provider-specific snapshots for reproducible inspection.
- `exports/` stores generated files for tools such as Zotero or CSV analysis.
- `public/` stores sanitized JSON for frontends and external consumers.

`state/` is the source for derived machine artifacts:

- `state/papers.jsonl` is the full cumulative paper library.
- `state/reading_status.json` is the long-term reading status center.
- `state/run_history.json` records daily pipeline runs.

`exports/` and `public/` are reproducible from `state/` plus the daily report
snapshots.

Do not commit credentials or private notes here.
