from __future__ import annotations

from dataclasses import asdict, dataclass, field as dataclass_field


@dataclass(frozen=True)
class PaperCandidate:
    id: str
    title: str
    authors: list[str]
    abstract: str
    source: str
    source_url: str
    pdf_url: str | None
    published_date: str | None
    categories: list[str]
    tags: list[str] = dataclass_field(default_factory=list)
    source_type: str = "recent_24h"
    source_group: str | None = None
    identifiers: dict[str, str] = dataclass_field(default_factory=dict)
    field: str | None = None
    venue: str | None = None
    classic_status: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Paper:
    id: str
    title: str
    source: str
    topics: list[str]
    url: str
    source_url: str | None = None
    title_zh: str | None = None
    field: str | None = None
    source_type: str | None = None
    source_group: str | None = None
    recommendation_level: str | None = None
    reading_advice: str | None = None
    code_url: str | None = None
    project_url: str | None = None
    citation_count: int | None = None
    venue: str | None = None
    difficulty: str | None = None
    why_recommended: str | None = None
    classic_status: str | None = None
    selected_for_s_level: bool = False
    score: float | None = None
    authors: list[str] = dataclass_field(default_factory=list)
    institutions: list[str] = dataclass_field(default_factory=list)
    categories: list[str] = dataclass_field(default_factory=list)
    tags: list[str] = dataclass_field(default_factory=list)
    abstract: str = ""
    pdf_url: str | None = None
    published_date: str | None = None
    published_at: str | None = None
    identifiers: dict[str, str] = dataclass_field(default_factory=dict)
    scores: dict[str, float] = dataclass_field(default_factory=dict)
    reading_status: str = "backlog"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class DailyReport:
    date: str
    generated_at: str
    summary: str
    papers: list[Paper] = dataclass_field(default_factory=list)
    learning_route_position: str | None = None
    source_mode_summary: dict[str, int] = dataclass_field(default_factory=dict)
    s_level_paper_id: str | None = None
    public_json_version: str = "0.2"
    generated_paths: dict[str, str] = dataclass_field(default_factory=dict)
    frontend_entry: str = "data/public/latest.json"
    s_level_candidate_ids: list[str] = dataclass_field(default_factory=list)
    knowledge_graph_delta: list[str] = dataclass_field(default_factory=list)
    next_actions: list[str] = dataclass_field(default_factory=list)

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["papers"] = [paper.to_dict() for paper in self.papers]
        return payload


@dataclass(frozen=True)
class ReadingStatus:
    paper_id: str
    status: str
    updated_at: str
    priority: str = "medium"
    notes_path: str | None = None
    history: list[dict] = dataclass_field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
