from __future__ import annotations

from dataclasses import replace
from difflib import SequenceMatcher
import json
import logging
import os
import re
import unicodedata
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from paper_learning.core.models import Paper
from paper_learning.enrichers.links import enrich_links

LOGGER = logging.getLogger(__name__)
SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1"
SEMANTIC_FIELDS = ",".join(
    [
        "title",
        "authors",
        "venue",
        "citationCount",
        "influentialCitationCount",
        "fieldsOfStudy",
        "externalIds",
        "openAccessPdf",
        "url",
        "year",
        "paperId",
    ]
)


class SemanticScholarClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        timeout: int = 20,
        base_url: str = SEMANTIC_SCHOLAR_API_URL,
    ) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = base_url.rstrip("/")

    @classmethod
    def from_env(cls, *, timeout: int = 20) -> "SemanticScholarClient":
        return cls(api_key=os.environ.get("SEMANTIC_SCHOLAR_API_KEY"), timeout=timeout)

    def enrich_paper(self, paper: Paper) -> Paper:
        try:
            payload = self._fetch_payload(paper)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            LOGGER.warning("Semantic Scholar enrichment failed for %s: %s", paper.id, exc)
            return enrich_links(paper)
        if not payload:
            return enrich_links(paper)
        return enrich_links(_merge_semantic_payload(paper, payload))

    def _fetch_payload(self, paper: Paper) -> dict | None:
        lookup = _lookup_target(paper)
        if lookup:
            method, lookup_id = lookup
            url = f"{self.base_url}/paper/{quote(lookup_id, safe=':')}?{urlencode({'fields': SEMANTIC_FIELDS})}"
            payload = self._read_json(url)
            if isinstance(payload, dict):
                LOGGER.info("Semantic Scholar lookup method=%s matched paper_id=%s", method, paper.id)
                return payload
            LOGGER.warning(
                "Semantic Scholar lookup method=%s rejected paper_id=%s reason=invalid_payload",
                method,
                paper.id,
            )
            return None

        query = paper.title.strip()
        if not _title_fallback_allowed(paper):
            LOGGER.info(
                "Semantic Scholar lookup method=title rejected paper_id=%s reason=title_too_broad",
                paper.id,
            )
            return None
        url = f"{self.base_url}/paper/search?{urlencode({'query': query, 'limit': 5, 'fields': SEMANTIC_FIELDS})}"
        payload = self._read_json(url)
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            LOGGER.warning(
                "Semantic Scholar lookup method=title rejected paper_id=%s reason=invalid_search_payload",
                paper.id,
            )
            return None
        rejected_reasons: list[str] = []
        for result in data:
            if not isinstance(result, dict):
                rejected_reasons.append("invalid_result")
                continue
            accepted, method, reason = _match_title_result(paper, result)
            if accepted:
                LOGGER.info(
                    "Semantic Scholar lookup method=%s matched paper_id=%s",
                    method,
                    paper.id,
                )
                return result
            rejected_reasons.append(reason)
        LOGGER.warning(
            "Semantic Scholar lookup method=title rejected paper_id=%s reason=%s",
            paper.id,
            ",".join(rejected_reasons) or "no_results",
        )
        return None

    def _read_json(self, url: str) -> dict:
        headers = {"User-Agent": "paper-learning-system/0.3"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        request = Request(url, headers=headers)
        with urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))


def enrich_papers(
    papers: list[Paper],
    *,
    semantic_config: dict | None = None,
    client: SemanticScholarClient | None = None,
) -> list[Paper]:
    config = semantic_config or {}
    if config.get("enabled", True) is False:
        return [enrich_links(paper) for paper in papers]

    active_client = client or SemanticScholarClient.from_env(timeout=int(config.get("timeout_seconds", 20)))
    max_with_key = int(config.get("max_enrichments_per_run", len(papers)))
    max_without_key = int(config.get("max_without_api_key", min(3, len(papers))))
    max_items = max_with_key if active_client.api_key else max_without_key

    selected_indexes = set(_select_enrichment_indexes(papers, max_items))
    enriched: list[Paper] = []
    for index, paper in enumerate(papers):
        if index in selected_indexes:
            enriched.append(active_client.enrich_paper(paper))
        else:
            enriched.append(enrich_links(paper))
    return enriched


def _lookup_target(paper: Paper) -> tuple[str, str] | None:
    external = {**paper.identifiers, **paper.external_ids}
    for key in ("DOI", "doi"):
        if external.get(key):
            return "exact_doi", f"DOI:{external[key]}"
    for key in ("ArXiv", "ARXIV", "arxiv_id"):
        if external.get(key):
            return "exact_arxiv", f"ARXIV:{external[key]}"
    for key in ("CorpusId", "corpus_id"):
        if external.get(key):
            return "exact_corpus_id", f"CorpusId:{external[key]}"
    for key in ("paperId", "paper_id", "semantic_scholar_id"):
        if external.get(key):
            return "exact_paper_id", str(external[key])
    return None


def _select_enrichment_indexes(papers: list[Paper], budget: int) -> list[int]:
    """Allocate a deterministic budget fairly across source groups."""

    if budget <= 0:
        return []
    tiers: list[list[tuple[int, Paper]]] = [[], [], [], []]
    for index, paper in enumerate(papers):
        reliable = _lookup_target(paper) is not None
        classic = paper.source_type == "classic"
        tier = (0 if reliable else 2) + (1 if classic else 0)
        tiers[tier].append((index, paper))

    selected: list[int] = []
    for tier in tiers:
        for index in _round_robin_indexes(tier):
            selected.append(index)
            if len(selected) >= min(budget, len(papers)):
                return selected
    return selected


def _round_robin_indexes(items: list[tuple[int, Paper]]) -> list[int]:
    groups: dict[str, list[int]] = {}
    order: list[str] = []
    for index, paper in items:
        group = paper.source_group or paper.source or "ungrouped"
        if group not in groups:
            groups[group] = []
            order.append(group)
        groups[group].append(index)

    result: list[int] = []
    offset = 0
    while True:
        added = False
        for group in order:
            indexes = groups[group]
            if offset < len(indexes):
                result.append(indexes[offset])
                added = True
        if not added:
            return result
        offset += 1


def _normalize_title(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = re.sub(r"[^\w\s]", " ", normalized, flags=re.UNICODE)
    return re.sub(r"\s+", " ", normalized).strip()


def _title_fallback_allowed(paper: Paper) -> bool:
    normalized = _normalize_title(paper.title)
    tokens = normalized.split()
    if len(tokens) < 4 or len(normalized) < 18:
        return False
    if paper.source_type == "classic" and len(tokens) < 6:
        return False
    return True


def _match_title_result(paper: Paper, result: dict) -> tuple[bool, str, str]:
    original = _normalize_title(paper.title)
    candidate = _normalize_title(str(result.get("title") or ""))
    if not candidate:
        return False, "title", "missing_title"

    exact = original == candidate
    similarity = SequenceMatcher(None, original, candidate).ratio()
    if not exact and similarity < 0.92:
        return False, "title", "title_mismatch"

    paper_authors = _normalized_authors(paper.authors)
    result_authors = _normalized_authors(
        [
            str(author.get("name") or "")
            for author in result.get("authors") or []
            if isinstance(author, dict)
        ]
    )
    if paper_authors and result_authors and not paper_authors.intersection(result_authors):
        return False, "title", "author_mismatch"

    paper_year = _paper_year(paper)
    result_year = _as_year(result.get("year"))
    if paper_year is not None and result_year is not None and abs(paper_year - result_year) > 1:
        return False, "title", "year_mismatch"

    if exact:
        return True, "exact_title", "matched"
    if not paper_authors or not result_authors:
        return False, "title", "fuzzy_requires_author"
    return True, "fuzzy_title_author_year", "matched"


def _normalized_authors(authors: list[str]) -> set[str]:
    normalized: set[str] = set()
    for author in authors:
        value = _normalize_title(author)
        if value:
            normalized.add(value)
            normalized.add(value.split()[-1])
    return normalized


def _paper_year(paper: Paper) -> int | None:
    value = paper.published_date or paper.published_at
    return _as_year(str(value)[:4]) if value else None


def _as_year(value: object) -> int | None:
    try:
        year = int(value)
    except (TypeError, ValueError):
        return None
    return year if 1000 <= year <= 9999 else None


def _merge_semantic_payload(paper: Paper, payload: dict) -> Paper:
    external_ids = {
        **paper.external_ids,
        **{str(key): str(value) for key, value in dict(payload.get("externalIds") or {}).items() if value},
    }
    identifiers = {**paper.identifiers, **external_ids}
    authors = paper.authors or [
        str(author.get("name"))
        for author in payload.get("authors", [])
        if isinstance(author, dict) and author.get("name")
    ]
    fields_of_study = paper.fields_of_study or [str(value) for value in payload.get("fieldsOfStudy") or [] if value]
    open_access_pdf = payload.get("openAccessPdf") if isinstance(payload.get("openAccessPdf"), dict) else {}
    enrichment_sources = list(dict.fromkeys([*paper.enrichment_sources, "semantic_scholar"]))

    return replace(
        paper,
        authors=authors,
        venue=paper.venue or payload.get("venue"),
        citation_count=_int_or_none(payload.get("citationCount"), paper.citation_count),
        influential_citation_count=_int_or_none(
            payload.get("influentialCitationCount"),
            paper.influential_citation_count,
        ),
        fields_of_study=fields_of_study,
        field=paper.field or (fields_of_study[0] if fields_of_study else None),
        external_ids=external_ids,
        identifiers=identifiers,
        open_access_pdf_url=paper.open_access_pdf_url or open_access_pdf.get("url"),
        enrichment_sources=enrichment_sources,
    )


def _int_or_none(value: object, fallback: int | None) -> int | None:
    if value is None:
        return fallback
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback
