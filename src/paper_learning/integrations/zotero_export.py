from __future__ import annotations


def build_zotero_export(papers: list[dict]) -> dict:
    return {"format": "zotero-placeholder", "items": papers}
