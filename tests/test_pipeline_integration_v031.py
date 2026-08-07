from dataclasses import replace
import json
from pathlib import Path
import shutil

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from referencing import Registry, Resource

from paper_learning.core.daily_pipeline import run_daily_pipeline
from paper_learning.core.models import PaperCandidate
from paper_learning.core.state_store import load_papers, load_reading_statuses, set_reading_status
from paper_learning.enrichers.links import enrich_links


def _candidate(
    paper_id: str,
    title: str,
    *,
    source: str,
    source_group: str,
    doi: str | None = None,
    source_type: str = "recent_7d",
) -> PaperCandidate:
    identifiers = {"doi": doi} if doi else {}
    return PaperCandidate(
        id=paper_id,
        title=title,
        authors=["Ada Lovelace"],
        abstract="A deterministic fixture with code https://github.com/example/code",
        source=source,
        source_url=f"https://example.com/{paper_id}",
        pdf_url=None,
        published_date="2026-07-10",
        categories=["cs.AI"] if source_group == "llm_agent" else ["neuroscience"],
        tags=[source_group],
        source_type=source_type,
        source_group=source_group,
        identifiers=identifiers,
        external_ids={"DOI": doi} if doi else {},
    )


class _SemanticClient:
    api_key = None

    def __init__(self) -> None:
        self.calls: list[str] = []

    def enrich_paper(self, paper):
        self.calls.append(paper.id)
        return enrich_links(
            replace(
                paper,
                citation_count=100,
                venue=paper.venue or "ICLR",
                enrichment_sources=[*paper.enrichment_sources, "semantic_scholar"],
            )
        )


def _fixture_root(tmp_path: Path) -> Path:
    for name in ("config", "curriculum", "schemas"):
        shutil.copytree(Path(name), tmp_path / name)
    return tmp_path


def _schema_registry(schema_dir: Path) -> Registry:
    registry = Registry()
    for path in schema_dir.glob("*.schema.json"):
        schema = json.loads(path.read_text(encoding="utf-8"))
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
        registry = registry.with_resource(path.name, Resource.from_contents(schema))
    return registry


def _validate(schema_dir: Path, schema_name: str, payload: dict) -> None:
    schema = json.loads((schema_dir / schema_name).read_text(encoding="utf-8"))
    Draft202012Validator(
        schema,
        registry=_schema_registry(schema_dir),
        format_checker=FormatChecker(),
    ).validate(payload)


def test_full_fixture_pipeline_is_idempotent_and_schema_valid(tmp_path, monkeypatch) -> None:
    root = _fixture_root(tmp_path)
    duplicate_doi = "10.1234/shared"
    arxiv = [
        _candidate(
            "arxiv:2607.00001",
            "Shared Cross Source Paper",
            source="arxiv",
            source_group="llm_agent",
            doi=duplicate_doi,
            source_type="recent_24h",
        ),
        _candidate(
            "arxiv:2607.00002",
            "Agent Planning with Reliable Tools",
            source="arxiv",
            source_group="llm_agent",
            doi="10.1234/agent",
        ),
    ]
    openreview = [
        _candidate(
            "openreview:shared",
            "Shared Cross Source Paper",
            source="openreview",
            source_group="llm_agent",
            doi=duplicate_doi,
            source_type="conference_review",
        )
    ]
    biorxiv = [
        _candidate(
            "biorxiv:10.1101/cognition",
            "Memory Guided Decisions in Neural Circuits",
            source="biorxiv",
            source_group="cognition_social",
            doi="10.1101/cognition",
        )
    ]
    client = _SemanticClient()
    monkeypatch.setattr(
        "paper_learning.core.daily_pipeline.fetch_recent_candidates_by_group",
        lambda _config, **_kwargs: arxiv,
    )
    monkeypatch.setattr(
        "paper_learning.core.daily_pipeline.fetch_openreview_candidates_by_config",
        lambda _config, **_kwargs: openreview,
    )
    monkeypatch.setattr(
        "paper_learning.core.daily_pipeline.fetch_biorxiv_candidates_by_config",
        lambda _config, **_kwargs: biorxiv,
    )
    monkeypatch.setattr(
        "paper_learning.enrichers.semantic_scholar.SemanticScholarClient.from_env",
        lambda **_kwargs: client,
    )

    report, _markdown, json_path = run_daily_pipeline("2026-07-13", root=root)
    selected_id = report.papers[0].id
    set_reading_status(
        selected_id,
        root=root,
        status="queued",
        updated_at="2026-07-13T12:00:00+00:00",
    )
    second_report, _markdown, _json = run_daily_pipeline("2026-07-13", root=root)

    assert 1 <= len(report.papers) <= 6
    assert len({paper.id for paper in load_papers(root)}) == len(load_papers(root))
    assert sum(1 for paper in report.papers if paper.selected_for_s_level) <= 1
    assert sum(1 for paper in load_papers(root) if paper.title == "Shared Cross Source Paper") == 1
    assert any("semantic_scholar" in paper.enrichment_sources for paper in report.papers)
    assert all("total" in paper.scores for paper in report.papers)
    assert load_reading_statuses(root)[selected_id].status == "queued"
    assert len(load_reading_statuses(root)) == len(load_papers(root))
    assert len(second_report.papers) <= 6
    assert [paper.id for paper in second_report.papers] == [
        paper.id for paper in report.papers
    ]
    assert [paper.score for paper in second_report.papers] == [
        paper.score for paper in report.papers
    ]

    schema_dir = root / "schemas"
    _validate(
        schema_dir,
        "daily_report.schema.json",
        json.loads(json_path.read_text(encoding="utf-8")),
    )
    public_schema = {
        "latest.json": "latest.schema.json",
        "daily_index.json": "daily_index.schema.json",
        "papers_index.json": "papers_index.schema.json",
        "knowledge_graph.json": "knowledge_graph.schema.json",
        "reading_status.json": "reading_status.schema.json",
        "curriculum_progress.json": "curriculum_progress.schema.json",
        "notes_index.json": "notes_index.schema.json",
    }
    for filename, schema_name in public_schema.items():
        payload = json.loads((root / "data/public" / filename).read_text(encoding="utf-8"))
        _validate(schema_dir, schema_name, payload)
    for paper in load_papers(root):
        _validate(schema_dir, "paper.schema.json", paper.to_dict())


def test_schema_rejects_additional_paper_property(tmp_path) -> None:
    root = _fixture_root(tmp_path)
    schema_dir = root / "schemas"
    payload = {
        "id": "p1",
        "title": "Paper",
        "source": "manual",
        "topics": ["llm_agent"],
        "url": "https://example.com",
        "unexpected": True,
    }

    with pytest.raises(ValidationError, match="Additional properties"):
        _validate(schema_dir, "paper.schema.json", payload)


def test_all_live_sources_empty_still_uses_classic_fallback(tmp_path, monkeypatch) -> None:
    root = _fixture_root(tmp_path)
    monkeypatch.setattr(
        "paper_learning.core.daily_pipeline.fetch_recent_candidates_by_group",
        lambda _config, **_kwargs: [],
    )
    monkeypatch.setattr(
        "paper_learning.core.daily_pipeline.fetch_openreview_candidates_by_config",
        lambda _config, **_kwargs: [],
    )
    monkeypatch.setattr(
        "paper_learning.core.daily_pipeline.fetch_biorxiv_candidates_by_config",
        lambda _config, **_kwargs: [],
    )
    monkeypatch.setattr(
        "paper_learning.enrichers.semantic_scholar.SemanticScholarClient.from_env",
        lambda **_kwargs: _SemanticClient(),
    )

    report, _markdown, _json = run_daily_pipeline("2026-07-13", root=root)

    assert report.papers
    assert all(paper.source_type == "classic" for paper in report.papers)
