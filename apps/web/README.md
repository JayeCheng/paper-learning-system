# Web Frontend

This directory is reserved for a future static web frontend.

Suitable implementations include:

- Astro for content-heavy static pages
- Next.js for richer interactions
- Docusaurus for documentation-style navigation

## Data Contract

The web app must consume only stable JSON:

- `data/public/*.json`
- structured daily JSON next to `daily/*.md`

It must not parse free-form Markdown as its primary data source and must not read
internal checkpoints from `data/state/`.

`data/public/notes_index.json` exposes Notion and local Markdown note entry metadata.
The frontend may render those links and the `note_count`, `latest_note_url`, and
`deep_read_note_url` fields in `papers_index.json`. It must not call or depend on the
Notion API; GitHub public JSON is the stable contract.

## Initial Views

- daily radar timeline
- topic dashboards
- S-level deep-read list
- curriculum roadmap
- knowledge graph browser
- Notion/local note entry links
