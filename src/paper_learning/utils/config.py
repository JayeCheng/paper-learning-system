from __future__ import annotations

import re
from pathlib import Path


DEFAULT_ARXIV_CATEGORIES = ["cs.AI", "cs.LG", "cs.CL", "cs.AR", "cs.DC", "cs.GR"]
DEFAULT_ARXIV_WINDOWS = {"recent_24h": 1, "recent_7d": 7}
DEFAULT_ARXIV_SOURCE_GROUPS = {
    "default": {
        "categories": list(DEFAULT_ARXIV_CATEGORIES),
        "max_results_per_window": 40,
        "target_min_daily": 0,
    }
}
DEFAULT_RANKING_WEIGHTS = {
    "recency": 0.25,
    "user_relevance": 0.30,
    "source_quality": 0.15,
    "engineering_transferability": 0.20,
    "classic_value": 0.10,
}
DEFAULT_OPENREVIEW_CONFIG = {
    "enabled": False,
    "venues": ["ICLR", "NeurIPS", "ICML", "COLM", "ACL", "EMNLP"],
    "venue_ids": [],
    "years": [2026, 2025],
    "max_results_per_venue": 10,
}
DEFAULT_BIORXIV_CONFIG = {
    "enabled": False,
    "servers": ["biorxiv", "medrxiv"],
    "categories": ["neuroscience", "animal behavior and cognition"],
    "window_days": 7,
    "max_results": 20,
    "query": None,
}
DEFAULT_SEMANTIC_SCHOLAR_CONFIG = {
    "enabled": True,
    "max_enrichments_per_run": 12,
    "max_without_api_key": 3,
    "timeout_seconds": 20,
}
DEFAULT_SOURCE_QUALITY = {
    "arxiv": 0.78,
    "openreview": 0.88,
    "biorxiv": 0.68,
    "semantic_scholar_enriched": 0.82,
    "manual_classic": 0.80,
    "github": 0.60,
    "manual": 0.55,
}


def load_arxiv_source_config(path: Path = Path("config/sources.yaml")) -> dict:
    config = {
        "categories": list(DEFAULT_ARXIV_CATEGORIES),
        "windows": dict(DEFAULT_ARXIV_WINDOWS),
        "max_results_per_window": 40,
        "source_groups": {name: dict(group) for name, group in DEFAULT_ARXIV_SOURCE_GROUPS.items()},
    }
    if not path.exists():
        return config

    lines = path.read_text(encoding="utf-8").splitlines()
    in_arxiv = False
    collecting_categories = False
    in_source_groups = False
    current_group: str | None = None
    current_window: str | None = None
    categories: list[str] = []
    source_groups: dict[str, dict] = {}

    for line in lines:
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))
        if indent == 2 and stripped.endswith(":"):
            in_arxiv = stripped == "arxiv:"
            collecting_categories = False
            in_source_groups = False
            current_group = None
            current_window = None
            continue
        if not in_arxiv:
            continue
        if stripped == "source_groups:":
            in_source_groups = True
            collecting_categories = False
            current_group = None
            current_window = None
            continue
        if in_source_groups and indent == 6 and stripped.endswith(":"):
            current_group = stripped[:-1]
            source_groups[current_group] = {
                "categories": [],
                "max_results_per_window": int(config["max_results_per_window"]),
                "target_min_daily": 0,
            }
            continue
        if in_source_groups and indent == 8 and current_group and ":" in stripped:
            key, raw_value = stripped.split(":", 1)
            value = _parse_scalar(raw_value)
            if key == "categories":
                source_groups[current_group]["categories"] = list(value) if isinstance(value, list) else []
            elif key in {"max_results_per_window", "target_min_daily"}:
                source_groups[current_group][key] = int(value)
            else:
                source_groups[current_group][key] = value
            continue
        if in_source_groups and indent <= 4 and stripped:
            in_source_groups = False
            current_group = None
        if stripped == "categories:":
            collecting_categories = True
            current_window = None
            continue
        if collecting_categories and stripped.startswith("- "):
            categories.append(_parse_scalar(stripped[2:]))
            continue
        if indent <= 4 and collecting_categories and stripped and not stripped.startswith("- "):
            collecting_categories = False
        if stripped.startswith("max_results_per_window:"):
            config["max_results_per_window"] = int(stripped.split(":", 1)[1].strip())
            continue
        if stripped in ("recent_24h:", "recent_7d:"):
            current_window = stripped[:-1]
            continue
        if current_window and stripped.startswith("days:"):
            config["windows"][current_window] = int(stripped.split(":", 1)[1].strip())

    if categories:
        config["categories"] = categories
    if source_groups:
        for group in source_groups.values():
            if not group.get("categories"):
                group["categories"] = list(config["categories"])
            group["max_results_per_window"] = int(
                group.get("max_results_per_window", config["max_results_per_window"])
            )
            group["target_min_daily"] = int(group.get("target_min_daily", 0))
        config["source_groups"] = source_groups
        config["categories"] = sorted(
            {category for group in source_groups.values() for category in group.get("categories", [])}
        )
    else:
        config["source_groups"] = {
            "default": {
                "categories": list(config["categories"]),
                "max_results_per_window": int(config["max_results_per_window"]),
                "target_min_daily": 0,
            }
        }
    return config


def load_ranking_config(path: Path = Path("config/ranking.yaml")) -> dict:
    config = {
        "max_daily_papers": 6,
        "max_s_level_papers": 1,
        "s_level_threshold": 0.88,
        "a_level_threshold": 0.74,
        "b_level_threshold": 0.58,
        "weights": dict(DEFAULT_RANKING_WEIGHTS),
        "source_quality": dict(DEFAULT_SOURCE_QUALITY),
    }
    if not path.exists():
        return config

    section: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line.startswith(" ") and stripped.endswith(":"):
            section = stripped[:-1]
            continue
        if ":" not in stripped:
            continue
        key, raw_value = stripped.split(":", 1)
        value = _parse_scalar(raw_value)
        if section == "ranking" and key in config:
            config[key] = value
        elif section == "weights" and key in config["weights"]:
            config["weights"][key] = float(value)
        elif section == "source_quality":
            config["source_quality"][key] = float(value)
    return config


def load_openreview_source_config(path: Path = Path("config/sources.yaml")) -> dict:
    return _load_source_section(path, "openreview", DEFAULT_OPENREVIEW_CONFIG)


def load_biorxiv_source_config(path: Path = Path("config/sources.yaml")) -> dict:
    return _load_source_section(path, "biorxiv", DEFAULT_BIORXIV_CONFIG)


def load_semantic_scholar_source_config(path: Path = Path("config/sources.yaml")) -> dict:
    return _load_source_section(path, "semantic_scholar", DEFAULT_SEMANTIC_SCHOLAR_CONFIG)


def load_classic_items(curriculum_dir: Path = Path("curriculum")) -> list[dict]:
    items: list[dict] = []
    if not curriculum_dir.exists():
        return items

    for path in sorted(curriculum_dir.glob("*_classics.yaml")):
        track = path.name.replace("_classics.yaml", "")
        current: dict | None = None
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("track:"):
                track = str(_parse_scalar(stripped.split(":", 1)[1]))
            elif stripped.startswith("- title:"):
                if current:
                    items.append(current)
                current = {"track": track, "title": _parse_scalar(stripped.split(":", 1)[1])}
            elif current and ":" in stripped:
                key, raw_value = stripped.split(":", 1)
                current[key] = _parse_scalar(raw_value)
        if current:
            items.append(current)
    return items


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "untitled"


def _load_source_section(path: Path, source_name: str, defaults: dict) -> dict:
    config = dict(defaults)
    if not path.exists():
        return config

    in_source = False
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))
        if indent == 2 and stripped.endswith(":"):
            in_source = stripped == f"{source_name}:"
            continue
        if not in_source:
            continue
        if indent <= 2 and stripped:
            break
        if indent == 4 and ":" in stripped:
            key, raw_value = stripped.split(":", 1)
            if key in config:
                config[key] = _parse_scalar(raw_value)
    return config


def _parse_scalar(value: str) -> object:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(item.strip()) for item in inner.split(",")]
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value
