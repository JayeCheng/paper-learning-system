from paper_learning.core.curriculum import recommend_next_readings


def test_recommend_next_readings_skips_finished_items() -> None:
    ranked = [
        {"id": "already-read"},
        {"id": "next"},
        {"id": "later"},
    ]
    status = {"already-read": "deep_read"}

    assert recommend_next_readings(ranked, status, limit=1) == [{"id": "next"}]
