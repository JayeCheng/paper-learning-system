from __future__ import annotations


def describe_commit_plan(paths: list[str]) -> dict:
    return {"strategy": "pull_request", "paths": paths}
