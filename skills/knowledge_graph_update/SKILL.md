# Knowledge Graph Update

## Purpose

Update topic maps and machine-readable graph deltas after reading.

## Inputs

- daily report
- deep-read notes
- existing `knowledge_graph/*.md`

## Outputs

- Markdown topic map edits
- future JSON graph payloads under `data/public/`

## Boundaries

- Do not invent unsupported edges.
- Preserve uncertainty when relationships are weak.
- Do not make frontend consumers parse Markdown as their only source.
