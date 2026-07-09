from __future__ import annotations

import csv
import json
from pathlib import Path

from paper_learning.core.models import Paper, ReadingStatus
from paper_learning.core.state_store import apply_reading_statuses

PAPER_EXPORT_FIELDS = [
    "id",
    "title",
    "source",
    "source_type",
    "source_group",
    "recommendation_level",
    "score",
    "published_date",
    "url",
    "topics",
    "categories",
    "reading_status",
]

READING_STATUS_EXPORT_FIELDS = [
    "paper_id",
    "status",
    "priority",
    "notes_path",
    "updated_at",
    "title",
    "source_group",
    "recommendation_level",
]


def write_exports(
    *,
    papers: list[Paper],
    reading_statuses: dict[str, ReadingStatus],
    exports_dir: Path = Path("data/exports"),
    daily_papers: list[Paper] | None = None,
) -> dict[str, Path]:
    exports_dir.mkdir(parents=True, exist_ok=True)
    papers_with_status = apply_reading_statuses(papers, reading_statuses)
    paths = {
        "papers_jsonl": exports_dir / "papers.jsonl",
        "papers_csv": exports_dir / "papers.csv",
        "reading_status_csv": exports_dir / "reading_status.csv",
    }

    _write_jsonl(paths["papers_jsonl"], [paper.to_dict() for paper in papers_with_status])
    _write_csv(paths["papers_csv"], [_paper_row(paper) for paper in papers_with_status], PAPER_EXPORT_FIELDS)
    _write_csv(
        paths["reading_status_csv"],
        _reading_status_rows(papers_with_status, reading_statuses),
        READING_STATUS_EXPORT_FIELDS,
    )

    if daily_papers is not None:
        daily_with_status = apply_reading_statuses(daily_papers, reading_statuses)
        paths["daily_papers_csv"] = exports_dir / "daily_papers.csv"
        _write_csv(paths["daily_papers_csv"], [_paper_row(paper) for paper in daily_with_status], PAPER_EXPORT_FIELDS)

    return paths


def _paper_row(paper: Paper) -> dict:
    row = paper.to_dict()
    row["topics"] = ";".join(paper.topics)
    row["categories"] = ";".join(paper.categories)
    return row


def _reading_status_rows(papers: list[Paper], statuses: dict[str, ReadingStatus]) -> list[dict]:
    paper_map = {paper.id: paper for paper in papers}
    rows: list[dict] = []
    all_ids = sorted({*paper_map, *statuses})
    for paper_id in all_ids:
        paper = paper_map.get(paper_id)
        status = statuses.get(paper_id)
        rows.append(
            {
                "paper_id": paper_id,
                "status": status.status if status else "backlog",
                "priority": status.priority if status else "medium",
                "notes_path": status.notes_path if status else None,
                "updated_at": status.updated_at if status else None,
                "title": paper.title if paper else "",
                "source_group": paper.source_group if paper else None,
                "recommendation_level": paper.recommendation_level if paper else None,
            }
        )
    return rows


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
