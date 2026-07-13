from __future__ import annotations

from dataclasses import replace
import json
import logging
import os
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
        lookup_id = _lookup_id(paper)
        if lookup_id:
            url = f"{self.base_url}/paper/{quote(lookup_id, safe=':')}?{urlencode({'fields': SEMANTIC_FIELDS})}"
            payload = self._read_json(url)
            return payload if isinstance(payload, dict) else None

        query = paper.title.strip()
        if not query:
            return None
        url = f"{self.base_url}/paper/search?{urlencode({'query': query, 'limit': 1, 'fields': SEMANTIC_FIELDS})}"
        payload = self._read_json(url)
        data = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(data, list) and data:
            first = data[0]
            return first if isinstance(first, dict) else None
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

    enriched: list[Paper] = []
    for index, paper in enumerate(papers):
        if index < max_items:
            enriched.append(active_client.enrich_paper(paper))
        else:
            enriched.append(enrich_links(paper))
    return enriched


def _lookup_id(paper: Paper) -> str | None:
    external = {**paper.identifiers, **paper.external_ids}
    for key in ("DOI", "doi"):
        if external.get(key):
            return f"DOI:{external[key]}"
    for key in ("ArXiv", "ARXIV", "arxiv_id"):
        if external.get(key):
            return f"ARXIV:{external[key]}"
    for key in ("CorpusId", "semantic_scholar_id"):
        if external.get(key):
            return str(external[key])
    return None


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
