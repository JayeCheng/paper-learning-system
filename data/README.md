# Data Directory

This directory stores repository-owned data.

- `state/` is durable internal state that automation may update through pull requests.
- `raw/` stores provider-specific snapshots for reproducible inspection.
- `exports/` stores generated files for tools such as Zotero or CSV analysis.
- `public/` stores sanitized JSON for frontends and external consumers.

Do not commit credentials or private notes here.
