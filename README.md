# paper-learning-system

Paper Radar + Curriculum Engine + Knowledge Graph + Archive + Integration Layer.

This repository is a long-lived, GitHub-first system for learning from research papers.
It is designed to collect promising papers, rank them, turn them into durable reading
artifacts, and expose machine-readable JSON for future integrations and web frontends.

Version `v0.3` builds on the stable backend loop with source enrichment. It can run
a daily paper radar, fetch recent arXiv metadata by configured topic groups, add
OpenReview and bioRxiv/medRxiv candidates, enrich metadata through Semantic Scholar
when available, discover code/project links without cloning repositories, and
maintain durable state plus derived public/export artifacts.

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
pip install -e ".[dev]"
make test
make daily
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m pytest
python scripts/run_daily.py
```

Run the daily radar through the installed CLI:

```bash
paper-learning daily --date today
paper-learning daily --date 2026-07-07
paper-learning status list
paper-learning status set arxiv:2601.00001v1 --status queued
paper-learning status set arxiv:2601.00001v1 --priority high
paper-learning status set arxiv:2601.00001v1 --notes-path deep_read/llm_agent/example.md
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
tests/             Minimal contract tests for the v0.0 skeleton.
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

`v0.3` implements source enrichment on top of the stable backend loop:

- arXiv metadata fetch for configured source groups and recent windows
- OpenReview metadata fetch for configured venues such as ICLR, NeurIPS, ICML,
  COLM, ACL, and EMNLP
- bioRxiv/medRxiv metadata fetch filtered to neuroscience, cognitive science, and
  behavior relevance
- optional Semantic Scholar metadata enrichment before ranking, with API-key-free
  degradation
- code and project link discovery from fetched metadata without cloning repositories
- classic curriculum fallback when recent candidates are insufficient
- normalize, dedupe, enrich, rank, and cap to six daily papers with soft source-group
  coverage
- at most one S-level paper per daily report
- stable daily Markdown/JSON, durable state, public JSON indexes, and CSV/JSONL exports
- durable `data/state/papers.jsonl`, `data/state/reading_status.json`, and
  `data/state/run_history.json`
- reading status CLI for backlog, queue, skim, deep-read, archive, and skip states

## Durable Data Semantics

- `data/state/papers.jsonl` is the full cumulative paper library.
- `data/state/reading_status.json` is the long-term reading status center.
- `data/state/run_history.json` records each daily pipeline run.
- `data/exports/papers.csv` and `data/exports/papers.jsonl` are full-library exports.
- `data/exports/daily_papers.csv` is the latest daily selected-paper export.
- `data/exports/reading_status.csv` is the full reading-status export.
- `data/public/*.json` is the only stable frontend entry layer.

Not yet implemented:

- Notion synchronization beyond a mock placeholder
- Zotero export beyond placeholders
- PDF download or parsing
- vector databases or semantic search
- web frontend
- database-backed storage
