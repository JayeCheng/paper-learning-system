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
  -> src/paper_learning/enrichers
  -> src/paper_learning/core/rank.py
  -> src/paper_learning/core/curriculum.py
  -> src/paper_learning/reports
  -> daily/YYYY/MM/*.md and daily/YYYY/MM/*.json
  -> src/paper_learning/core/state_store.py
  -> data/state/*.json, data/state/*.jsonl
  -> data/exports/* and data/public/*.json
  -> integrations
```

## Module Boundaries

- `fetchers/` only fetch source data. Fetchers do not rank, update reading state, or
  publish to integrations.
- `enrichers/` only enrich already-normalized metadata before ranking. Enrichers may
  call metadata APIs, but they do not select recommendations, render reports, clone
  repositories, or download PDFs.
- `core/rank.py` only scores normalized paper records. It does not access the network.
- `reports/` only renders Markdown and JSON from prepared data. It does not fetch.
- `core/state_store.py` owns durable repository state reads and writes.
- `integrations/` only syncs to external systems. It does not decide recommendations.
- `skills/` documents stable agent workflows. Skills do not store state and do not
  directly access external APIs.
- `data/public/` is the frontend contract. Frontends must not parse `data/state/`.

## Scheduling

The daily report target time is `06:10` in Asia/Singapore. GitHub Actions cron is
defined in UTC, so the workflow uses `10 22 * * *`, which corresponds to `22:10`
UTC on the previous day.

## Topic Group Fetching

`config/sources.yaml` defines arXiv `source_groups`. The arXiv fetcher still only
fetches metadata; the daily pipeline calls it once per group and recency window, then
normalization, dedupe, and ranking decide the daily selection. `source_group` is kept
on candidates and normalized papers so later ranking and public JSON can preserve the
originating topic lane.

## Source Enrichment

`config/sources.yaml` controls optional v0.3 sources:

- OpenReview fetches conference-review metadata for configured venues or explicit
  venue IDs.
- bioRxiv/medRxiv fetches recent preprint metadata only for neuroscience, cognitive
  science, and behavior-relevant categories or keywords.
- Semantic Scholar is metadata enrichment only. It can add citation counts, venue,
  fields of study, external IDs, and open-access PDF URLs, but it is not a primary
  recommendation source.

All enrichment runs before `core/rank.py`. Ranking consumes local fields such as
`citation_count`, `code_url`, `venue`, and `field`, and must remain network-free.

## State Model

GitHub owns long-term state:

- Markdown reports and deep reads provide human-readable archives.
- JSON files provide machine-readable contracts.
- `data/state/` stores internal state that automation may update.
- `data/public/` stores sanitized, frontend-ready JSON.
- `data/exports/` stores reproducible derived files for spreadsheet and tool review.

Notion, Zotero, and future dashboards are downstream views. They can be rebuilt from
GitHub state.

## Data Contracts

Schemas live in `schemas/`:

- `paper.schema.json` describes normalized paper metadata.
- `daily_report.schema.json` describes daily report payloads.
- `latest.schema.json`, `daily_index.schema.json`, and `papers_index.schema.json`
  describe frontend entrypoint files.
- `knowledge_graph.schema.json` describes nodes and typed edges.
- `reading_status.schema.json` describes public reading progress.
- `curriculum_progress.schema.json` describes frontend-ready route progress.

Schema changes should be reviewed as public API changes once consumers exist.

## Frontend Extension Design

The future web app under `apps/web/` should consume only:

- `data/public/*.json`
- structured daily JSON next to `daily/*.md`

It should not parse free-form Markdown or internal state. Astro, Next.js, or
Docusaurus can all fit this model as long as the build step treats JSON as the stable
interface and Markdown as a human archive.

## v0.3 State Files

- `data/state/papers.jsonl`: full cumulative normalized paper library, including
  source enrichment fields when available.
- `data/state/reading_status.json`: long-term human/automation reading state.
- `data/state/run_history.json`: one entry per successful daily pipeline run, including
  date, generated paths, paper count, S-level paper id, and status.

Derived files must be regenerated from this state:

- `data/exports/papers.csv` and `data/exports/papers.jsonl`: full paper library.
- `data/exports/daily_papers.csv`: latest daily selection.
- `data/exports/reading_status.csv`: full reading-status table.
- `data/public/*.json`: stable, schema-backed frontend contract.

## v0.3 Non-Goals

- No complex crawler implementation.
- No live Notion or Zotero synchronization.
- No database dependency.
- No PDF download or parsing.
- No ranking model beyond deterministic local scoring.
- No web frontend beyond documentation.
