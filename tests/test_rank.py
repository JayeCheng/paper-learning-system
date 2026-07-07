from paper_learning.core.rank import rank_papers, score_paper


def test_score_paper_is_deterministic_and_bounded() -> None:
    paper = {
        "id": "p1",
        "source": "openreview",
        "topics": ["llm_agent"],
        "scores": {"topic_match": 1.0, "recency": 0.8, "citations": 100},
    }

    score = score_paper(paper)

    assert score == score_paper(paper)
    assert 0 <= score <= 1


def test_rank_papers_orders_by_score() -> None:
    low = {"id": "low", "source": "manual", "topics": [], "scores": {"topic_match": 0.1}}
    high = {"id": "high", "source": "openreview", "topics": ["architecture"], "scores": {"topic_match": 1.0}}

    assert rank_papers([low, high])[0] == high
