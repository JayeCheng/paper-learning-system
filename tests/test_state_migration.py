import json

import pytest

from paper_learning.core.state_migration import migrate_v03_state


FAKE_CODE_URL = (
    "https://github.com/JayeCheng/paper-learning-system/"
    "blob/main/curriculum/cognition_classics.yaml"
)


def _write_fixture(root, *, code_url=FAKE_CODE_URL, topics=None) -> None:
    state = root / "data/state"
    state.mkdir(parents=True)
    paper = {
        "id": "classic:cognition:attention",
        "title": "Attention and working memory",
        "source": "manual",
        "source_type": "classic",
        "source_group": "cognition",
        "topics": topics or ["uncategorized"],
        "categories": ["cognition"],
        "tags": ["classic", "cognition"],
        "field": "cognition",
        "url": FAKE_CODE_URL,
        "source_url": FAKE_CODE_URL,
        "code_url": code_url,
        "manual_note": "preserve this custom field",
    }
    (state / "papers.jsonl").write_text(json.dumps(paper) + "\n", encoding="utf-8")
    reading = {
        "state_version": "0.3",
        "updated_at": "2026-07-13T00:00:00+00:00",
        "items": {
            paper["id"]: {
                "paper_id": paper["id"],
                "status": "deep_read",
                "priority": "high",
                "notes_path": "deep_read/attention.md",
                "updated_at": "2026-07-13T00:00:00+00:00",
                "history": [{"at": "2026-07-13T00:00:00+00:00", "status": "deep_read"}],
            }
        },
    }
    (state / "reading_status.json").write_text(json.dumps(reading), encoding="utf-8")
    (state / "run_history.json").write_text(
        json.dumps(
            {
                "state_version": "0.3",
                "updated_at": "2026-07-13T00:00:00+00:00",
                "runs": [],
            }
        ),
        encoding="utf-8",
    )


def _read_paper(root) -> dict:
    return json.loads((root / "data/state/papers.jsonl").read_text(encoding="utf-8"))


def test_migration_dry_run_does_not_write(tmp_path) -> None:
    _write_fixture(tmp_path)
    before = (tmp_path / "data/state/papers.jsonl").read_bytes()

    result = migrate_v03_state(root=tmp_path, dry_run=True)

    assert result.changed_papers == 1
    assert set(result.changes[0].fields) == {"code_url", "topics"}
    assert (tmp_path / "data/state/papers.jsonl").read_bytes() == before
    assert not (tmp_path / "data/public").exists()


def test_migration_cleans_state_preserves_reading_data_and_is_idempotent(tmp_path) -> None:
    _write_fixture(tmp_path)

    first = migrate_v03_state(root=tmp_path)
    paper = _read_paper(tmp_path)
    reading = json.loads((tmp_path / "data/state/reading_status.json").read_text(encoding="utf-8"))
    second = migrate_v03_state(root=tmp_path)

    assert first.changed_papers == 1
    assert paper["code_url"] is None
    assert paper["topics"] == ["cognition"]
    assert paper["manual_note"] == "preserve this custom field"
    assert reading["items"][paper["id"]]["status"] == "deep_read"
    assert reading["items"][paper["id"]]["priority"] == "high"
    assert reading["items"][paper["id"]]["history"]
    assert second.changed_papers == 0
    assert (tmp_path / "data/exports/papers.jsonl").exists()
    assert (tmp_path / "data/public/papers_index.json").exists()


def test_migration_preserves_real_repository_url(tmp_path) -> None:
    real_url = "https://github.com/example/real-implementation"
    _write_fixture(tmp_path, code_url=real_url, topics=["cognition"])

    result = migrate_v03_state(root=tmp_path)

    assert result.changed_papers == 0
    assert _read_paper(tmp_path)["code_url"] == real_url


def test_atomic_write_failure_leaves_original_intact(tmp_path, monkeypatch) -> None:
    _write_fixture(tmp_path)
    path = tmp_path / "data/state/papers.jsonl"
    before = path.read_bytes()

    def fail_replace(_source, _target):
        raise OSError("simulated replace failure")

    monkeypatch.setattr("paper_learning.core.state_migration.os.replace", fail_replace)

    with pytest.raises(OSError, match="simulated"):
        migrate_v03_state(root=tmp_path)

    assert path.read_bytes() == before
