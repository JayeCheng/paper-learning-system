# Public Data

`data/public/` is the stable JSON interface for future frontends and external tools.

Rules:

- Include only sanitized, public, non-secret data.
- Prefer schema-backed JSON.
- Do not require consumers to parse free-form Markdown.
- Do not expose internal checkpoint details from `data/state/`.
