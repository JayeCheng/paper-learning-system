# Skill Governance

Repository skills describe stable, repeatable AI-agent workflows.

They are not runtime state, not code replacements, and not a place to hide tool-specific
logic. The Python package owns implementation. GitHub owns durable state.

## Current Skill Budget

The repository allows at most six stable skills without an explicit architecture review:

1. `paper_radar`
2. `paper_ranking`
3. `s_level_deep_read`
4. `knowledge_graph_update`
5. `curriculum_planner`
6. `notion_publish`

## Rules

- Prefer editing an existing skill before adding a new one.
- Each skill must name its inputs, outputs, and forbidden responsibilities.
- Skills must not store reading state or credentials.
- Skills must not directly access external APIs when a repository module should do it.
- Skills should call scripts or modules rather than duplicating logic.
