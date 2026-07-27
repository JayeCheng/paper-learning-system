import json

from paper_learning.core.models import Paper
from paper_learning.core.notes_index import (
    add_note,
    annotate_report_papers,
    link_knowledge_node,
    load_notes,
    update_note,
)
from paper_learning.core.state_store import upsert_papers
from paper_learning.reports.daily_report import build_daily_report
from paper_learning.reports.markdown_renderer import render_daily_markdown


def _paper(*, selected_for_s_level: bool = False) -> Paper:
    return Paper(
        id="arxiv:2607.00001",
        title="Metadata Bridges for Research Notes",
        source="arxiv",
        source_type="recent_7d",
        source_group="llm_agent",
        topics=["llm_agent"],
        url="https://example.com/paper",
        selected_for_s_level=selected_for_s_level,
        recommendation_level="S" if selected_for_s_level else "A",
    )


def test_notes_index_add_update_and_link(tmp_path) -> None:
    upsert_papers([_paper()], root=tmp_path)

    note = add_note(
        paper_id="arxiv:2607.00001",
        note_type="deep_read",
        title="Deep Read: Metadata Bridges",
        notion_url="https://www.notion.so/deep-read",
        local_markdown_path="deep_read/llm_agent/metadata-bridges.md",
        tags=["notion", "bridge", "notion"],
        root=tmp_path,
        timestamp="2026-07-27T10:00:00+00:00",
    )
    updated = update_note(
        note.note_id,
        status="published",
        root=tmp_path,
        timestamp="2026-07-27T11:00:00+00:00",
    )
    linked = link_knowledge_node(
        note.note_id,
        knowledge_node="notion-metadata-bridge",
        root=tmp_path,
        timestamp="2026-07-27T12:00:00+00:00",
    )
    link_knowledge_node(
        note.note_id,
        knowledge_node="notion-metadata-bridge",
        root=tmp_path,
        timestamp="2026-07-27T13:00:00+00:00",
    )

    stored = load_notes(tmp_path)[0]
    payload = json.loads((tmp_path / "data/state/notes_index.json").read_text(encoding="utf-8"))

    assert note.note_id.startswith("note:deep_read:deep-read-metadata-bridges-")
    assert note.created_at == note.updated_at
    assert note.tags == ["notion", "bridge"]
    assert updated.status == "published"
    assert linked.linked_knowledge_nodes == ["notion-metadata-bridge"]
    assert stored.linked_knowledge_nodes == ["notion-metadata-bridge"]
    assert payload["state_version"] == "0.4"


def test_s_level_report_gets_note_bridge_fields(tmp_path) -> None:
    paper = _paper(selected_for_s_level=True)
    upsert_papers([paper], root=tmp_path)
    note = add_note(
        paper_id=paper.id,
        note_type="deep_read",
        title="Existing Deep Read",
        notion_url="https://www.notion.so/existing",
        root=tmp_path,
        timestamp="2026-07-27T10:00:00+00:00",
    )

    annotated = annotate_report_papers([paper], [note])
    report = build_daily_report(annotated, date="2026-07-27")
    markdown = render_daily_markdown(report)

    assert annotated[0].existing_note_url == "https://www.notion.so/existing"
    assert annotated[0].suggested_note_type == "deep_read"
    assert annotated[0].suggested_note_title == "Deep Read: Metadata Bridges for Research Notes"
    assert "Existing note: https://www.notion.so/existing" in markdown


def test_note_add_rejects_unknown_paper(tmp_path) -> None:
    try:
        add_note(
            paper_id="missing",
            note_type="deep_read",
            title="Missing",
            notion_url="https://www.notion.so/missing",
            root=tmp_path,
        )
    except ValueError as exc:
        assert "does not exist" in str(exc)
    else:
        raise AssertionError("unknown paper should be rejected")
