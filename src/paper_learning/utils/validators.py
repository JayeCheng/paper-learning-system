from __future__ import annotations


def require_keys(payload: dict, keys: list[str]) -> None:
    missing = [key for key in keys if key not in payload]
    if missing:
        raise ValueError(f"Missing required keys: {', '.join(missing)}")
