from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import logging
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from paper_learning.core.models import PaperCandidate

LOGGER = logging.getLogger(__name__)
BIORXIV_API_URL = "https://api.biorxiv.org/details"

DEFAULT_SERVERS = ["biorxiv", "medrxiv"]
DEFAULT_CATEGORIES = [
    "neuroscience",
    "animal behavior and cognition",
]
RELEVANCE_KEYWORDS = {
    "attention",
    "behavior",
    "behaviour",
    "brain",
    "cognition",
    "cognitive",
    "decision",
    "learning",
    "memory",
    "neural",
    "neuroscience",
    "perception",
    "psychology",
    "social",
}


def fetch_biorxiv_candidates(
    *,
    query: str | None = None,
    categories: list[str] | None = None,
    servers: list[str] | None = None,
    window_days: int = 7,
    limit: int = 20,
    now: datetime | None = None,
) -> list[PaperCandidate]:
    """Fetch bioRxiv/medRxiv metadata for cognition-related candidates.

    The fetcher deliberately filters for cognitive science, neuroscience, and
    behavior signals so broad biomedical records do not enter the recommender just
    because they are recent.
    """

    active_servers = servers or DEFAULT_SERVERS
    active_categories = categories or DEFAULT_CATEGORIES
    timestamp = now or datetime.now(timezone.utc)
    interval = _interval(timestamp, window_days)

    candidates: list[PaperCandidate] = []
    try:
        for server in active_servers:
            for category in active_categories:
                payload = _fetch_details_payload(server=server, interval=interval, category=category)
                candidates.extend(
                    _parse_biorxiv_payload(
                        payload,
                        server=server,
                        query=query,
                        limit=max(0, limit - len(candidates)),
                    )
                )
                if len(candidates) >= limit:
                    return candidates[:limit]
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        LOGGER.warning("bioRxiv/medRxiv fetch failed: %s", exc)
        return []

    return candidates[:limit]


def _fetch_details_payload(*, server: str, interval: str, category: str | None) -> dict:
    safe_server = server.lower()
    url = f"{BIORXIV_API_URL}/{safe_server}/{interval}/0/json"
    if category:
        url = f"{url}?{urlencode({'category': category})}"
    request = Request(url, headers={"User-Agent": "paper-learning-system/0.3"})
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _parse_biorxiv_payload(
    payload: dict,
    *,
    server: str,
    query: str | None,
    limit: int,
) -> list[PaperCandidate]:
    collection = payload.get("collection") if isinstance(payload, dict) else []
    if not isinstance(collection, list) or limit <= 0:
        return []

    candidates: list[PaperCandidate] = []
    for item in collection:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        abstract = str(item.get("abstract") or "").strip()
        category = str(item.get("category") or "").strip()
        doi = str(item.get("doi") or "").strip()
        if not title or not doi:
            continue
        if not _is_relevant(title=title, abstract=abstract, category=category, query=query):
            continue

        venue = "medRxiv" if server.lower() == "medrxiv" else "bioRxiv"
        candidates.append(
            PaperCandidate(
                id=f"biorxiv:{doi}",
                title=title,
                authors=_split_authors(str(item.get("authors") or "")),
                abstract=abstract,
                source="biorxiv",
                source_url=f"https://doi.org/{doi}",
                pdf_url=None,
                published_date=str(item.get("date") or "")[:10] or None,
                categories=[category] if category else [],
                tags=[tag for tag in [category, "cognition_social", server.lower()] if tag],
                source_type="recent_7d",
                source_group="cognition_social",
                identifiers={"doi": doi, "server": server.lower()},
                external_ids={"DOI": doi},
                venue=venue,
                fields_of_study=["Neuroscience"] if "neuro" in category.lower() else ["Psychology"],
            )
        )
        if len(candidates) >= limit:
            break
    return candidates


def _interval(now: datetime, window_days: int) -> str:
    end = now.date()
    start = (now - timedelta(days=window_days)).date()
    return f"{start.isoformat()}/{end.isoformat()}"


def _split_authors(value: str) -> list[str]:
    separator = ";" if ";" in value else ","
    return [author.strip() for author in value.split(separator) if author.strip()]


def _is_relevant(*, title: str, abstract: str, category: str, query: str | None) -> bool:
    haystack = " ".join([title, abstract, category]).lower()
    if query and query.lower() not in haystack:
        return False
    category_lower = category.lower()
    if any(keyword in category_lower for keyword in RELEVANCE_KEYWORDS):
        return True
    return any(keyword in haystack for keyword in RELEVANCE_KEYWORDS)
