from paper_learning.core.models import Paper
from paper_learning.enrichers.semantic_scholar import enrich_papers


def test_enrichment_pipeline_preserves_existing_fields_and_discovers_links() -> None:
    paper = Paper(
        id="p1",
        title="Existing Metadata",
        source="arxiv",
        source_type="recent_24h",
        topics=["architecture"],
        url="https://arxiv.org/abs/2601.00001",
        authors=["Original Author"],
        citation_count=5,
        abstract=(
            "Code is available at https://github.com/example/project and "
            "the project page is https://example.org/project."
        ),
    )

    enriched = enrich_papers([paper], semantic_config={"enabled": False})[0]

    assert enriched.title == "Existing Metadata"
    assert enriched.authors == ["Original Author"]
    assert enriched.citation_count == 5
    assert enriched.code_url == "https://github.com/example/project"
    assert enriched.project_url == "https://example.org/project"
