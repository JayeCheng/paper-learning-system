# State

`data/state/` is for durable machine state owned by GitHub.

Examples:

- normalized paper indexes
- reading status maps
- dedupe fingerprints
- report generation checkpoints

Frontends must not consume this directory directly. Publish sanitized contracts to
`data/public/` instead.
