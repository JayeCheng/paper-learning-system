# Paper Radar

## Purpose

Collect candidate papers for the daily radar.

## Inputs

- `config/topics.yaml`
- `config/sources.yaml`
- source snapshots under `data/raw/`

## Outputs

- normalized candidates for ranking
- optional raw metadata snapshots

## Boundaries

- Fetch only.
- Do not rank papers.
- Do not update reading state.
- Do not publish to Notion or Zotero.
