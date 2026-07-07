# Notion Publish

## Purpose

Publish selected report views to Notion.

## Inputs

- daily Markdown report
- structured daily JSON
- `config/integrations.yaml`

## Outputs

- Notion page or database updates

## Boundaries

- Notion is not primary storage.
- Do not write tokens to the repository.
- Do not let Notion schema drive the repository schema.
