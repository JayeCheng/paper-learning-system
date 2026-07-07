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

## Initial Views

- daily radar timeline
- topic dashboards
- S-level deep-read list
- curriculum roadmap
- knowledge graph browser
