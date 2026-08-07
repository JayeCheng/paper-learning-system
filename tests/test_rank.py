from paper_learning.core.models import Paper
import pytest

from paper_learning.core.rank import rank_papers, score_factors, score_paper, select_ranked_papers


def test_score_paper_is_deterministic_and_bounded() -> None:
    paper = {
        "id": "p1",
        "source": "openreview",
        "topics": ["llm_agent"],
        "source_type": "recent_24h",
        "scores": {"user_relevance": 1.0, "recency": 0.8},
    }

    score = score_paper(paper)

    assert score == score_paper(paper)
    assert 0 <= score <= 1


def test_rank_papers_orders_by_score() -> None:
    low = {"id": "low", "source": "manual", "topics": [], "scores": {"topic_match": 0.1}}
    high = {"id": "high", "source": "openreview", "topics": ["architecture"], "scores": {"topic_match": 1.0}}

    assert rank_papers([low, high])[0] == high


def test_enriched_metadata_improves_local_score_without_network() -> None:
    base = {
        "id": "base",
        "source": "arxiv",
        "topics": ["llm_agent"],
        "source_type": "recent_7d",
        "categories": ["cs.CL"],
    }
    enriched = {
        **base,
        "id": "enriched",
        "citation_count": 120,
        "influential_citation_count": 12,
        "venue": "ICLR",
        "field": "Computer Science",
        "code_url": "https://github.com/example/project",
        "enrichment_sources": ["semantic_scholar"],
    }

    assert score_paper(enriched) > score_paper(base)


def test_select_ranked_papers_limits_daily_and_s_level() -> None:
    papers = [
        Paper(
            id=f"p{i}",
            title=f"Paper {i}",
            source="arxiv",
            source_type="recent_24h",
            topics=["llm_agent"],
            categories=["cs.AI"],
            url=f"https://example.com/{i}",
            published_date="2026-07-07",
            scores={
                "recency": 1.0,
                "user_relevance": 1.0,
                "source_quality": 1.0,
                "engineering_transferability": 1.0,
                "classic_value": 1.0,
            },
        )
        for i in range(8)
    ]
    ranking_config = {
        "max_daily_papers": 6,
        "max_s_level_papers": 1,
        "s_level_threshold": 0.88,
        "a_level_threshold": 0.74,
        "b_level_threshold": 0.58,
        "weights": {
            "recency": 0.25,
            "user_relevance": 0.30,
            "source_quality": 0.15,
            "engineering_transferability": 0.20,
            "classic_value": 0.10,
        },
    }

    selected = select_ranked_papers(papers, ranking_config=ranking_config, report_date="2026-07-07")

    assert len(selected) == 6
    assert sum(1 for paper in selected if paper.recommendation_level == "S") == 1


@pytest.mark.parametrize(
    ("published_date", "expected"),
    [
        ("2026-07-12", 1.0),
        ("2026-07-08", 0.78),
        ("2026-06-13", 0.55),
        ("2025-07-13", 0.35),
        (None, 0.35),
    ],
)
def test_openreview_recency_uses_real_date(published_date, expected) -> None:
    paper = {
        "source": "openreview",
        "source_type": "conference_review",
        "published_date": published_date,
        "topics": ["llm_agent"],
    }

    assert score_factors(paper, report_date="2026-07-13")["recency"] == expected


def test_published_date_wins_over_conflicting_recent_source_type() -> None:
    paper = {
        "source": "openreview",
        "source_type": "recent_7d",
        "published_date": "2025-01-01",
        "topics": ["llm_agent"],
        "scores": {"recency": 1.0},
    }

    assert score_factors(paper, report_date="2026-07-13")["recency"] == 0.35


def test_future_paper_never_receives_highest_recency_score() -> None:
    paper = {
        "source": "arxiv",
        "source_type": "recent_24h",
        "published_date": "2026-07-14",
        "topics": ["llm_agent"],
    }

    assert score_factors(paper, report_date="2026-07-13")["recency"] == 0.0
