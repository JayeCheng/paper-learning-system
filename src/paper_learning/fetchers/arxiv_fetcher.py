from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from paper_learning.core.models import PaperCandidate

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def fetch_arxiv_candidates(
    *,
    categories: list[str] | None = None,
    source_type: str = "recent_24h",
    window_days: int = 1,
    max_results: int = 40,
    now: datetime | None = None,
) -> list[PaperCandidate]:
    """Fetch arXiv candidates and filter them to the requested recency window.

    The fetcher owns network access only. Ranking and rendering stay in core/report
    modules. Network failures return an empty list so the daily pipeline can fall back
    to classics.
    """

    categories = categories or ["cs.AI"]
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)
    query = " OR ".join(f"cat:{category}" for category in categories)
    params = urlencode(
        {
            "search_query": query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "start": 0,
            "max_results": max_results,
        }
    )
    request = Request(f"{ARXIV_API_URL}?{params}", headers={"User-Agent": "paper-learning-system/0.1"})

    try:
        with urlopen(request, timeout=20) as response:
            payload = response.read()
    except OSError:
        return []

    return _parse_arxiv_atom(payload, source_type=source_type, cutoff=cutoff)


def _parse_arxiv_atom(payload: bytes, *, source_type: str, cutoff: datetime) -> list[PaperCandidate]:
    root = ET.fromstring(payload)
    candidates: list[PaperCandidate] = []
    for entry in root.findall("atom:entry", ATOM_NS):
        published = _text(entry, "atom:published")
        published_dt = _parse_arxiv_datetime(published)
        if published_dt and published_dt < cutoff:
            continue

        source_url = _text(entry, "atom:id")
        arxiv_id = source_url.rsplit("/", 1)[-1] if source_url else _text(entry, "arxiv:doi")
        categories = [node.attrib.get("term", "") for node in entry.findall("atom:category", ATOM_NS)]
        categories = [category for category in categories if category]
        pdf_url = _pdf_link(entry)

        candidates.append(
            PaperCandidate(
                id=f"arxiv:{arxiv_id}",
                title=_text(entry, "atom:title"),
                authors=[_text(author, "atom:name") for author in entry.findall("atom:author", ATOM_NS)],
                abstract=_text(entry, "atom:summary"),
                source="arxiv",
                source_url=source_url,
                pdf_url=pdf_url,
                published_date=published[:10] if published else None,
                categories=categories,
                tags=categories,
                source_type=source_type,
                identifiers={"arxiv_id": arxiv_id},
            )
        )
    return candidates


def _text(node: ET.Element, path: str) -> str:
    child = node.find(path, ATOM_NS)
    return " ".join((child.text or "").split()) if child is not None else ""


def _pdf_link(entry: ET.Element) -> str | None:
    for link in entry.findall("atom:link", ATOM_NS):
        if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
            return link.attrib.get("href")
    return None


def _parse_arxiv_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None
