from paper_learning.core.normalize import normalize_paper


def test_category_topic_mapping_for_core_tracks() -> None:
    assert _topic_for("cs.GR") == "gpu_graphics"
    assert _topic_for("cs.AR") == "architecture"
    assert _topic_for("cs.CL") == "llm_agent"


def _topic_for(category: str) -> str:
    paper = normalize_paper(
        {
            "id": f"paper-{category}",
            "title": "Mapped Paper",
            "source": "arxiv",
            "source_url": "https://example.com",
            "categories": [category],
            "tags": [category],
        }
    )
    return paper.topics[0]
