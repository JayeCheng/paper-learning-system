from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from paper_learning.core.models import PaperCandidate

LOGGER = logging.getLogger(__name__)
OPENREVIEW_API_URL = "https://api2.openreview.net/notes"
OPENREVIEW_FORUM_URL = "https://openreview.net/forum"

DEFAULT_VENUES = ["ICLR", "NeurIPS", "ICML", "COLM", "ACL", "EMNLP"]
DEFAULT_YEARS = [2026, 2025]
VENUE_ID_TEMPLATES = {
    "ICLR": "ICLR.cc/{year}/Conference",
    "NEURIPS": "NeurIPS.cc/{year}/Conference",
    "ICML": "ICML.cc/{year}/Conference",
    "COLM": "colmweb.org/COLM/{year}/Conference",
    "ACL": "aclweb.org/ACL/{year}/Conference",
    "EMNLP": "aclweb.org/EMNLP/{year}/Conference",
}


def fetch_openreview_candidates(
    *,
    venue: str | None = None,
    venues: list[str] | None = None,
    venue_ids: list[str] | None = None,
    years: list[int] | None = None,
    limit: int = 20,
) -> list[PaperCandidate]:
    """Fetch OpenReview submissions as source candidates.

    This fetcher only collects metadata. Ranking and reading-state decisions stay in
    core modules. API failures degrade to an empty list so the daily pipeline can
    continue with other sources and classic fallback.
    """

    candidates: list[PaperCandidate] = []
    ids = _venue_ids(venue=venue, venues=venues, venue_ids=venue_ids, years=years)
    if not ids:
        return candidates

    try:
        for venue_id in ids:
            payload = _fetch_notes_payload(venue_id=venue_id, limit=limit)
            candidates.extend(_parse_openreview_notes(payload, venue_id=venue_id))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        LOGGER.warning("OpenReview fetch failed: %s", exc)
        return []

    return candidates


def _fetch_notes_payload(*, venue_id: str, limit: int) -> dict:
    query = urlencode(
        {
            "content.venueid": venue_id,
            "limit": limit,
            "sort": "tmdate:desc",
        }
    )
    request = Request(
        f"{OPENREVIEW_API_URL}?{query}",
        headers={"User-Agent": "paper-learning-system/0.3"},
    )
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _parse_openreview_notes(payload: dict, *, venue_id: str) -> list[PaperCandidate]:
    notes = payload.get("notes") if isinstance(payload, dict) else []
    if not isinstance(notes, list):
        return []

    candidates: list[PaperCandidate] = []
    for note in notes:
        if not isinstance(note, dict):
            continue
        content = note.get("content") if isinstance(note.get("content"), dict) else {}
        note_id = str(note.get("id") or note.get("forum") or "")
        if not note_id:
            continue

        title = str(_content_value(content, "title") or "").strip()
        abstract = str(_content_value(content, "abstract") or "").strip()
        if not title:
            continue

        authors = _as_string_list(_content_value(content, "authors"))
        venue_label = _venue_label(content, venue_id)
        source_url = f"{OPENREVIEW_FORUM_URL}?id={note.get('forum') or note_id}"
        pdf_url = _openreview_pdf_url(_content_value(content, "pdf"))
        published_date = _openreview_date(note, content)

        candidates.append(
            PaperCandidate(
                id=f"openreview:{note_id}",
                title=title,
                authors=authors,
                abstract=abstract,
                source="openreview",
                source_url=source_url,
                pdf_url=pdf_url,
                published_date=published_date,
                categories=[venue_label] if venue_label else [],
                tags=[tag for tag in [venue_label, venue_id] if tag],
                source_type="recent_7d",
                source_group="llm_agent",
                identifiers={"openreview_id": note_id, "venue_id": venue_id},
                venue=venue_label,
            )
        )
    return candidates


def _venue_ids(
    *,
    venue: str | None,
    venues: list[str] | None,
    venue_ids: list[str] | None,
    years: list[int] | None,
) -> list[str]:
    explicit = [value for value in (venue_ids or []) if value]
    if explicit:
        return explicit

    venue_names = [venue] if venue else venues or DEFAULT_VENUES
    active_years = years or DEFAULT_YEARS
    ids: list[str] = []
    for name in venue_names:
        if not name:
            continue
        template = VENUE_ID_TEMPLATES.get(name.upper())
        if not template:
            ids.append(name)
            continue
        ids.extend(template.format(year=year) for year in active_years)
    return ids


def _content_value(content: dict, key: str) -> object:
    raw = content.get(key)
    if isinstance(raw, dict) and "value" in raw:
        return raw["value"]
    return raw


def _as_string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _venue_label(content: dict, venue_id: str) -> str:
    for key in ("venue", "venueid"):
        value = _content_value(content, key)
        if value:
            return str(value)
    return venue_id.split("/", 1)[0]


def _openreview_pdf_url(value: object) -> str | None:
    if not value:
        return None
    raw = str(value)
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    if raw.startswith("/"):
        return f"https://openreview.net{raw}"
    return None


def _openreview_date(note: dict, content: dict) -> str | None:
    year = _content_value(content, "year")
    if year:
        return f"{year}-01-01"
    for key in ("pdate", "cdate", "tmdate"):
        value = note.get(key)
        if isinstance(value, int) and value > 0:
            return datetime.fromtimestamp(value / 1000, timezone.utc).date().isoformat()
    return None
