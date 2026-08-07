from dataclasses import replace

from paper_learning.core.models import Paper
from paper_learning.enrichers.semantic_scholar import enrich_papers


def _paper(index: int, group: str, *, reliable: bool = True, classic: bool = False) -> Paper:
    return Paper(
        id=f"p{index}",
        title=f"A sufficiently specific research paper title {index}",
        source="manual",
        source_type="classic" if classic else "conference_review",
        source_group=group,
        topics=[group],
        url=f"https://example.com/{index}",
        identifiers={"doi": f"10.1/{index}"} if reliable else {},
    )


class _Client:
    def __init__(self, *, api_key=None) -> None:
        self.api_key = api_key
        self.calls: list[str] = []

    def enrich_paper(self, paper: Paper) -> Paper:
        self.calls.append(paper.id)
        return replace(paper, enrichment_sources=["semantic_scholar"])


def test_budget_round_robins_across_source_groups_deterministically() -> None:
    papers = [
        _paper(1, "first"),
        _paper(2, "first"),
        _paper(3, "first"),
        _paper(4, "second"),
        _paper(5, "third"),
    ]
    config = {"max_without_api_key": 3}
    first = _Client()
    second = _Client()

    enrich_papers(papers, semantic_config=config, client=first)
    enrich_papers(papers, semantic_config=config, client=second)

    assert first.calls == ["p1", "p4", "p5"]
    assert second.calls == first.calls


def test_reliable_ids_are_prioritized_over_unidentified_classics() -> None:
    papers = [
        _paper(1, "classic", reliable=False, classic=True),
        _paper(2, "live", reliable=True),
    ]
    client = _Client()

    enrich_papers(papers, semantic_config={"max_without_api_key": 1}, client=client)

    assert client.calls == ["p2"]


def test_zero_budget_still_runs_local_link_discovery() -> None:
    paper = replace(
        _paper(1, "group"),
        abstract="Code is available at https://github.com/example/repository",
    )
    client = _Client()

    result = enrich_papers([paper], semantic_config={"max_without_api_key": 0}, client=client)

    assert client.calls == []
    assert result[0].code_url == "https://github.com/example/repository"


def test_budget_larger_than_candidates_enriches_all() -> None:
    papers = [_paper(1, "a"), _paper(2, "b", reliable=False)]
    client = _Client(api_key="present")

    enrich_papers(papers, semantic_config={"max_enrichments_per_run": 20}, client=client)

    assert client.calls == ["p1", "p2"]
