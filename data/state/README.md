# State

`data/state/` is for durable machine state owned by GitHub.

Examples:

- `papers.jsonl`: full cumulative normalized paper library. Daily runs upsert into
  this file; they do not replace it with only the current day.
- `reading_status.json`: long-term reading status and priority for known papers.
- `run_history.json`: every successful daily pipeline run with date, generated paths,
  paper count, S-level paper id, and status.

Frontends must not consume this directory directly. Publish sanitized contracts to
`data/public/` instead.
