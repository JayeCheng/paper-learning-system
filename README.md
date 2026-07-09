# paper-learning-system

Paper Radar + Curriculum Engine + Knowledge Graph + Archive + Integration Layer.

This repository is a long-lived, GitHub-first system for learning from research papers.
It is designed to collect promising papers, rank them, turn them into durable reading
artifacts, and expose machine-readable JSON for future integrations and web frontends.

Version `v0.1` is a backend MVP. It can run a daily paper radar, fetch recent arXiv
metadata, fall back to classic curriculum items, rank candidates, and write stable
Markdown, JSON, and export artifacts.

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
fetchers -> normalize -> dedupe -> rank -> curriculum -> reports -> public JSON
                                              |
                                              v
                                      knowledge graph updates
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

`v0.1` implements a minimal backend loop:

- arXiv metadata fetch for configured categories and recent windows
- classic curriculum fallback when recent candidates are insufficient
- normalize, dedupe, rank, and cap to six daily papers
- at most one S-level paper per daily report
- stable daily Markdown/JSON, public JSON indexes, and CSV/JSONL exports

Not yet implemented:

- Notion synchronization beyond a mock placeholder
- Zotero export beyond placeholders
- PDF download or parsing
- vector databases or semantic search
- web frontend
- OpenReview, bioRxiv, Semantic Scholar, or GitHub production fetchers
