from __future__ import annotations

from dataclasses import dataclass
import logging
import os

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class NotionConfig:
    api_key: str | None
    database_id: str | None

    @classmethod
    def from_env(cls) -> "NotionConfig":
        return cls(
            api_key=os.environ.get("NOTION_API_KEY") or None,
            database_id=os.environ.get("NOTION_DATABASE_ID") or None,
        )

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.database_id)


def sync_note_metadata(*, config: NotionConfig | None = None) -> dict:
    """Return sync capability status without making a Notion API request.

    v0.4 intentionally keeps GitHub state authoritative. A future implementation
    may push metadata outward, but must not ingest Notion as durable source state.
    """

    active_config = config or NotionConfig.from_env()
    if not active_config.configured:
        LOGGER.info("Notion sync skipped: NOTION_API_KEY or NOTION_DATABASE_ID is missing.")
        return {
            "enabled": False,
            "skipped": True,
            "reason": "missing_configuration",
            "synced": 0,
        }
    LOGGER.info("Notion credentials detected; automatic sync is not implemented in v0.4.")
    return {
        "enabled": True,
        "skipped": True,
        "reason": "not_implemented",
        "synced": 0,
    }


def publish_to_notion(*, report_path: str) -> dict:
    """Backward-compatible placeholder for downstream presentation publishing."""

    result = sync_note_metadata()
    return {**result, "report_path": report_path}
