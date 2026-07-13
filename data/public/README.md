# Public Data

`data/public/` is the stable JSON interface for future frontends and external tools.

Rules:

- Include only sanitized, public, non-secret data.
- Prefer schema-backed JSON.
- Do not require consumers to parse free-form Markdown.
- Do not expose internal checkpoint details from `data/state/`.

Generated v0.2 files:

- `latest.json`: pointer to the latest daily Markdown and JSON report.
- `daily_index.json`: ordered index of daily reports.
- `papers_index.json`: normalized paper metadata for search and filtering.
- `knowledge_graph.json`: initial machine-readable graph of papers and topics.
- `reading_status.json`: public reading status and priority records.
- `curriculum_progress.json`: route progress derived from papers and status.
