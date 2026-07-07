from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Paper:
    id: str
    title: str
    source: str
    topics: list[str]
    url: str
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    pdf_url: str | None = None
    published_at: str | None = None
    identifiers: dict[str, str] = field(default_factory=dict)
    scores: dict[str, float] = field(default_factory=dict)
    reading_status: str = "backlog"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class DailyReport:
    date: str
    generated_at: str
    summary: str
    papers: list[Paper] = field(default_factory=list)
    s_level_candidate_ids: list[str] = field(default_factory=list)
    knowledge_graph_delta: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)

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
    history: list[dict] = field(default_factory=list)
