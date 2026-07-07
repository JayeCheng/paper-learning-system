# Paper Ranking

## Purpose

Score normalized paper candidates using the configured ranking policy.

## Inputs

- normalized paper records
- `config/ranking.yaml`
- curriculum context

## Outputs

- ranked candidates
- S-level candidate flags

## Boundaries

- Do not access the network.
- Do not fetch or publish.
- Do not mutate long-term state directly.
