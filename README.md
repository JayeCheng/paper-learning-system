# paper-learning-system

Paper Radar + Curriculum Engine + Knowledge Graph + Archive + Integration Layer.

This repository is a long-lived, GitHub-first system for learning from research papers.
It is designed to collect promising papers, rank them, turn them into durable reading
artifacts, and expose machine-readable JSON for future integrations and web frontends.

Version `v0.4` adds a Notion metadata bridge to the stabilized source-enrichment
backend. It can run
a daily paper radar, fetch recent arXiv metadata by configured topic groups, add
OpenReview and bioRxiv/medRxiv candidates, enrich metadata through Semantic Scholar
when available, discover code/project links without cloning repositories, and
maintain durable state plus derived public/export artifacts.

Notion remains a downstream presentation layer. GitHub state and
`data/public/*.json` remain the durable and frontend-facing contracts.

## Goals

- Track high-quality papers, technical reports, and preprints on a daily cadence.
- Support GPU / Graphics, Computer Architecture, LLM Agent / RAG, Cognitive Science,
  Behavioral Science, and Sociology.
- Generate daily Markdown learning reports for long-term reading.
- Maintain paper metadata, reading status, classic-paper roadmaps, and knowledge graph
  increments in Git.
- Later publish selected views to Notion, Zotero, and a static web frontend.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m compileall src scripts tests
python -m pytest
python scripts/run_daily.py --date today
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m compileall src scripts tests
python -m pytest
python scripts/run_daily.py --date today
```

Run the daily radar through the installed CLI:

```bash
paper-learning daily --date today
paper-learning daily --date 2026-07-07
paper-learning status list
paper-learning status set arxiv:2601.00001v1 --status queued
paper-learning status set arxiv:2601.00001v1 --priority high
paper-learning status set arxiv:2601.00001v1 --notes-path deep_read/llm_agent/example.md
paper-learning note list
paper-learning note add --paper-id arxiv:2601.00001v1 --type deep_read \
  --title "Deep Read: Example" --notion-url "https://www.notion.so/example"
paper-learning note add --paper-id arxiv:2601.00001v1 --type project_note \
  --title "Local Project Note" --local-markdown-path "deep_read/project-note.md"
paper-learning note update note:deep_read:deep-read-example-12345678 \
  --status published --local-markdown-path "deep_read/llm_agent/example.md"
paper-learning note link --note-id note:deep_read:deep-read-example-12345678 \
  --knowledge-node retrieval-augmented-generation
```

Or without installing the console script:

```bash
python scripts/run_daily.py --date today
python scripts/run_daily.py --date 2026-07-07
```

## Repository Layout

```text
config/            Stable YAML configuration for topics, sources, ranking, tools, and integrations.
data/state/        Durable machine state owned by GitHub.
data/raw/          Source snapshots grouped by upstream provider.
data/exports/      Export artifacts such as CSV, BibTeX, or Zotero payloads.
data/public/       JSON interface for frontends and external consumers.
daily/             Daily Markdown reports and paired JSON outputs under YYYY/MM.
deep_read/         Long-form paper notes grouped by learning track.
knowledge_graph/   Human-readable knowledge graph indexes and topic maps.
curriculum/        Classic-paper routes and planned learning sequences.
skills/            Stable AI-agent workflows, not state storage.
src/               Python package with fetch, core, report, and integration modules.
apps/web/          Placeholder for a future static visualization frontend.
schemas/           JSON Schemas for public and internal data contracts.
tests/             Contract, integration, regression, and CLI tests for the v0.4 baseline.
scripts/           Thin command wrappers for scheduled or manual operations.
```

## Data Flow

```text
fetchers -> normalize -> dedupe -> enrichment -> rank -> curriculum -> daily reports
                                                                  |
                                                                  v
                                                         data/state durable state
                                                                  |
                                                                  v
                                                    data/exports and data/public JSON
```

Core rules:

- GitHub is the only long-term source of truth.
- Markdown is the durable human archive.
- JSON is the machine interface for frontends, Notion, APIs, and search.
- `data/public/*.json` is the stable frontend entrypoint. Structured daily JSON lives
  under `daily/YYYY/MM/`.
- Notion is a presentation layer, not primary storage.

## Daily Schedule

The configured local report time is `06:10` in Asia/Singapore. GitHub Actions cron
uses UTC, so `06:10` SGT is scheduled as `22:10` UTC on the previous day:
`10 22 * * *`.

## Current Status

The current stable baseline is `v0.4`. It includes the v0.3.1 source-enrichment
stabilization plus the GitHub-owned Notion/local note metadata bridge:

- arXiv metadata fetch for configured source groups and recent windows
- OpenReview metadata fetch for configured venues such as ICLR, NeurIPS, ICML,
  COLM, ACL, and EMNLP, with per-venue failure isolation and date-based recency
- bioRxiv/medRxiv metadata fetch filtered to neuroscience, cognitive science, and
  behavior relevance
- optional Semantic Scholar metadata enrichment before ranking, with guarded
  title matching and deterministic cross-source-group budget allocation
- code and project link discovery from fetched metadata without cloning repositories
- classic curriculum fallback when recent candidates are insufficient
- normalize, dedupe, enrich, rank, and cap to six daily papers with soft source-group
  coverage
- at most one S-level paper per daily report
- stable daily Markdown/JSON, durable state, public JSON indexes, and CSV/JSONL exports
- durable `data/state/papers.jsonl`, `data/state/reading_status.json`, and
  `data/state/run_history.json`
- reading status CLI for backlog, queue, skim, deep-read, archive, and skip states

Independent GitHub fetching is not implemented. Code and project URLs are discovered
locally from paper metadata. The `rate_limit_per_minute` keys from v0.3 were removed
because no request boundary enforced them; provider-specific rate limiting remains a
planned capability rather than a production promise.

Run the explicit, idempotent state cleanup separately from the daily pipeline:

```bash
python scripts/migrate_v03_state.py --root . --dry-run
python scripts/migrate_v03_state.py --root .
python scripts/migrate_v03_state.py --root .
```

## Durable Data Semantics

- `data/state/papers.jsonl` is the full cumulative paper library.
- `data/state/reading_status.json` is the long-term reading status center.
- `data/state/run_history.json` records each daily pipeline run.
- `data/exports/papers.csv` and `data/exports/papers.jsonl` are full-library exports.
- `data/exports/daily_papers.csv` is the latest daily selected-paper export.
- `data/exports/reading_status.csv` is the full reading-status export.
- `data/public/*.json` is the only stable frontend entry layer.
- `data/state/notes_index.json` is the GitHub-owned metadata index for local and
  manually entered Notion note links.
- `data/public/notes_index.json` and `data/exports/notes_index.csv` are derived views
  for future frontends and spreadsheet review.

## Notion Metadata Bridge

Use `paper-learning note add` to record either a manually created Notion URL, a
repository-relative Markdown path, or both. The CLI validates locations before
writing state and does not contact Notion. `NOTION_API_KEY` and
`NOTION_DATABASE_ID` are optional; when absent, `scripts/sync_notion.py` exits
successfully with a skip message. Even when configured, v0.4 does not implement
automatic content sync.

Daily S-level papers include an existing note URL when available and a suggested
`deep_read` note title. Future frontends can show note entry links using
`data/public/notes_index.json` and the note summary fields in
`data/public/papers_index.json`, without loading the Notion API.

Not yet implemented:

- automatic Notion content synchronization
- Zotero export beyond placeholders
- PDF download or parsing
- vector databases or semantic search
- web frontend
- database-backed storage
