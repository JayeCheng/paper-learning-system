# paper-learning-system

Paper Radar + Curriculum Engine + Knowledge Graph + Archive + Integration Layer.

This repository is a long-lived, GitHub-first system for learning from research papers.
It is designed to collect promising papers, rank them, turn them into durable reading
artifacts, and expose machine-readable JSON for future integrations and web frontends.

Version `v0.0` is an architecture skeleton. It defines repository boundaries,
configuration, schemas, and safe extension points before adding complex fetch logic.

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

## Repository Layout

```text
config/            Stable YAML configuration for topics, sources, ranking, tools, and integrations.
data/state/        Durable machine state owned by GitHub.
data/raw/          Source snapshots grouped by upstream provider.
data/exports/      Export artifacts such as CSV, BibTeX, or Zotero payloads.
data/public/       JSON interface for frontends and external consumers.
daily/             Daily Markdown reports and future paired JSON outputs.
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
- `data/public/*.json` and structured daily JSON are the only frontend contracts.
- Notion is a presentation layer, not primary storage.

## Current Status

`v0.0` contains no production crawler. Fetchers are intentionally shallow placeholders
so module boundaries can harden before network behavior, ranking heuristics, and
scheduled automation expand.
