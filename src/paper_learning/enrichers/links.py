from __future__ import annotations

from dataclasses import replace
import re
from urllib.parse import urlparse

from paper_learning.core.models import Paper

URL_PATTERN = re.compile(r"https?://[^\s<>)\]}\"']+")
CODE_HOSTS = {"github.com", "www.github.com", "gitlab.com", "bitbucket.org"}
PROJECT_HOST_HINTS = ("github.io", "huggingface.co", "paperswithcode.com")
PROJECT_PATH_HINTS = ("project", "demo", "code", "software")
IGNORED_PROJECT_HOSTS = {
    "arxiv.org",
    "doi.org",
    "openreview.net",
    "api.semanticscholar.org",
    "semanticscholar.org",
    "www.semanticscholar.org",
}
IGNORED_REPOSITORY_PATHS = {
    ("github.com", "/jayecheng/paper-learning-system"),
    ("www.github.com", "/jayecheng/paper-learning-system"),
}


def enrich_links(paper: Paper) -> Paper:
    """Discover code and project links from already-fetched metadata only."""

    urls = _candidate_urls(paper)
    code_url = paper.code_url or _first_code_url(urls)
    project_url = paper.project_url or _first_project_url(urls, code_url=code_url)
    if code_url == paper.code_url and project_url == paper.project_url:
        return paper
    return replace(paper, code_url=code_url, project_url=project_url)


def discover_links(text: str) -> tuple[str | None, str | None]:
    urls = _urls_from_text(text)
    code_url = _first_code_url(urls)
    return code_url, _first_project_url(urls, code_url=code_url)


def _candidate_urls(paper: Paper) -> list[str]:
    text_values = [
        paper.abstract,
        paper.source_url or "",
        paper.url,
        paper.pdf_url or "",
        paper.open_access_pdf_url or "",
        *(paper.identifiers.values()),
        *(paper.external_ids.values()),
    ]
    urls: list[str] = []
    for value in text_values:
        urls.extend(_urls_from_text(str(value)))
    return urls


def _urls_from_text(text: str) -> list[str]:
    urls = []
    for match in URL_PATTERN.findall(text):
        urls.append(match.rstrip(".,;:"))
    return urls


def _first_code_url(urls: list[str]) -> str | None:
    for url in urls:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if host in CODE_HOSTS:
            if _is_ignored_repository_link(parsed):
                continue
            return url
    return None


def _first_project_url(urls: list[str], *, code_url: str | None) -> str | None:
    for url in urls:
        if url == code_url:
            continue
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path = parsed.path.lower()
        if host in IGNORED_PROJECT_HOSTS or path.endswith(".pdf") or _is_ignored_repository_link(parsed):
            continue
        if any(hint in host for hint in PROJECT_HOST_HINTS) or any(hint in path for hint in PROJECT_PATH_HINTS):
            return url
    return None


def _is_ignored_repository_link(parsed) -> bool:
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    return any(host == ignored_host and path.startswith(ignored_path) for ignored_host, ignored_path in IGNORED_REPOSITORY_PATHS)
