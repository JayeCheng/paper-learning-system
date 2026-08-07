from paper_learning.integrations.notion_client import (
    NotionConfig,
    publish_to_notion,
    sync_note_metadata,
)


def test_notion_sync_gracefully_skips_without_configuration(monkeypatch) -> None:
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)

    result = sync_note_metadata()

    assert NotionConfig.from_env().configured is False
    assert result == {
        "enabled": False,
        "skipped": True,
        "reason": "missing_configuration",
        "synced": 0,
    }


def test_notion_credentials_do_not_enable_content_sync(monkeypatch) -> None:
    monkeypatch.setenv("NOTION_API_KEY", "secret")
    monkeypatch.setenv("NOTION_DATABASE_ID", "database")

    result = sync_note_metadata()
    published = publish_to_notion(report_path="daily/example.md")

    assert NotionConfig.from_env().configured is True
    assert result["reason"] == "not_implemented"
    assert result["synced"] == 0
    assert published["report_path"] == "daily/example.md"
