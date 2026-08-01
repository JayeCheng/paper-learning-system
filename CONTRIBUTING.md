# Contributing

The current stable baseline is `v0.4`. Contributions should preserve the established
module boundaries while extending the GitHub-owned state and public JSON contracts.

## Development

```bash
pip install -e ".[dev]"
make test
make lint
```

## Guidelines

- Keep GitHub as the source of truth.
- Prefer small, reviewable changes.
- Do not commit API keys, tokens, cookies, or private notes.
- Do not make fetchers rank papers.
- Do not make renderers fetch data.
- Do not make integrations influence recommendation logic.
- Add or update schemas when JSON contracts change.
- Keep local-only experiments outside committed paths or behind `.gitignore`.

## Pull Requests

Each PR should include:

- A concise summary of behavior or structure changes.
- Tests or validation commands.
- Any schema or data contract impact.
- Any follow-up work that should remain out of scope.
