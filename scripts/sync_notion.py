from __future__ import annotations

from paper_learning.integrations.notion_client import sync_note_metadata


def main() -> int:
    result = sync_note_metadata()
    if result["reason"] == "missing_configuration":
        print("Notion sync skipped: NOTION_API_KEY and NOTION_DATABASE_ID are optional.")
    else:
        print("Notion sync skipped: automatic metadata sync is not implemented in v0.4.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
