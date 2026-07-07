import json
from pathlib import Path

from paper_learning.core.models import DailyReport, Paper


def test_schema_files_are_valid_json() -> None:
    for path in Path("schemas").glob("*.schema.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["type"] == "object"
        assert "properties" in payload


def test_paper_dataclass_fields_are_declared_in_schema() -> None:
    schema = json.loads(Path("schemas/paper.schema.json").read_text(encoding="utf-8"))
    paper = Paper(id="p1", title="Title", source="arxiv", topics=["llm_agent"], url="https://example.com")

    assert set(paper.to_dict()) <= set(schema["properties"])


def test_daily_report_fields_are_declared_in_schema() -> None:
    schema = json.loads(Path("schemas/daily_report.schema.json").read_text(encoding="utf-8"))
    report = DailyReport(date="2026-07-07", generated_at="2026-07-07T00:00:00+00:00", summary="Summary")

    assert set(report.to_dict()) <= set(schema["properties"])
