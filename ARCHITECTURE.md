# Architecture

`paper-learning-system` is a GitHub-first research learning system. The repository is
the durable state center; external products are presentation or synchronization
targets only.

## System Shape

```text
sources
  -> src/paper_learning/fetchers
  -> src/paper_learning/core/normalize.py
  -> src/paper_learning/core/dedupe.py
  -> src/paper_learning/core/rank.py
  -> src/paper_learning/core/curriculum.py
  -> src/paper_learning/reports
  -> daily/YYYY/MM/*.md, daily/YYYY/MM/*.json, and data/public/*.json
  -> integrations
```

## Module Boundaries

- `fetchers/` only fetch source data. Fetchers do not rank, update reading state, or
  publish to integrations.
- `core/rank.py` only scores normalized paper records. It does not access the network.
- `reports/` only renders Markdown and JSON from prepared data. It does not fetch.
- `integrations/` only syncs to external systems. It does not decide recommendations.
- `skills/` documents stable agent workflows. Skills do not store state and do not
  directly access external APIs.
- `data/public/` is the frontend contract. Frontends must not parse `data/state/`.

## Scheduling

The daily report target time is `06:10` in Asia/Singapore. GitHub Actions cron is
defined in UTC, so the workflow uses `10 22 * * *`, which corresponds to `22:10`
UTC on the previous day.

## State Model

GitHub owns long-term state:

- Markdown reports and deep reads provide human-readable archives.
- JSON files provide machine-readable contracts.
- `data/state/` stores internal state that automation may update.
- `data/public/` stores sanitized, frontend-ready JSON.

Notion, Zotero, and future dashboards are downstream views. They can be rebuilt from
GitHub state.

## Data Contracts

Schemas live in `schemas/`:

- `paper.schema.json` describes normalized paper metadata.
- `daily_report.schema.json` describes daily report payloads.
- `knowledge_graph.schema.json` describes nodes and typed edges.
- `reading_status.schema.json` describes reading progress.
- `curriculum_progress.schema.json` describes frontend-ready route progress.

Schema changes should be reviewed as public API changes once consumers exist.

## Frontend Extension Design

The future web app under `apps/web/` should consume only:

- `data/public/*.json`
- structured daily JSON next to `daily/*.md`

It should not parse free-form Markdown or internal state. Astro, Next.js, or
Docusaurus can all fit this model as long as the build step treats JSON as the stable
interface and Markdown as a human archive.

## v0.0 Non-Goals

- No complex crawler implementation.
- No live Notion or Zotero synchronization.
- No database dependency.
- No ranking model beyond deterministic placeholder scoring.
- No web frontend beyond documentation.
