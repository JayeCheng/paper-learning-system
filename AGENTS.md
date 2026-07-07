# Agent Rules

This file defines repository rules for Codex and other AI agents.

## Hard Rules

- Modify files only inside this repository.
- Do not create a nested `paper-learning-system/paper-learning-system` directory.
- Never commit API keys, tokens, cookies, private exports, or local credentials.
- Do not delete durable Markdown archives or state unless the user explicitly asks.
- Keep GitHub as the only long-term state center.
- Treat Notion, Zotero, dashboards, and chat tools as downstream views.

## Architecture Rules

- Fetchers fetch only. They do not rank, render, publish, or mutate reading state.
- `src/paper_learning/core/rank.py` scores only. It must not access the network.
- `src/paper_learning/reports/` renders only. It must not fetch source data.
- `src/paper_learning/integrations/` syncs only. It must not own recommendation logic.
- `skills/` stores workflow instructions only. It must not store runtime state.
- Frontends must consume `data/public/*.json` or structured daily JSON.

## Skill Governance

- Do not add more than six stable skills without an explicit architecture review.
- Prefer updating an existing skill over creating a new one.
- Skills should describe repeatable workflows, not ad hoc prompts.
- Skills should reference repository modules instead of duplicating logic.

## Before Finishing

- Run the relevant tests or explain why they could not be run.
- Inspect `git status --short`.
- Summarize changed files and any public schema impact.
