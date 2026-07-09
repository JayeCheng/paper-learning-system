from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from paper_learning.core.daily_pipeline import fetch_recent_candidates_by_group
from paper_learning.utils.config import load_arxiv_source_config


def test_topic_group_config_loads_source_groups() -> None:
    config = load_arxiv_source_config(Path("config/sources.yaml"))

    assert set(config["source_groups"]) == {"gpu_graphics", "architecture", "llm_agent", "cognition_social"}
    assert config["source_groups"]["gpu_graphics"]["categories"] == ["cs.GR", "cs.CV"]
    assert config["source_groups"]["llm_agent"]["max_results_per_window"] == 25
    assert config["source_groups"]["cognition_social"]["target_min_daily"] == 1


def test_legacy_arxiv_categories_become_default_source_group() -> None:
    with TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "sources.yaml"
        path.write_text(
            "\n".join(
                [
                    "sources:",
                    "  arxiv:",
                    "    max_results_per_window: 12",
                    "    categories:",
                    "      - cs.AI",
                    "      - cs.GR",
                ]
            ),
            encoding="utf-8",
        )

        config = load_arxiv_source_config(path)

        assert config["source_groups"]["default"]["categories"] == ["cs.AI", "cs.GR"]
        assert config["source_groups"]["default"]["max_results_per_window"] == 12


def test_fetch_recent_candidates_calls_arxiv_once_per_group_and_window() -> None:
    config = load_arxiv_source_config(Path("config/sources.yaml"))
    now = datetime(2026, 7, 9, tzinfo=timezone.utc)

    with patch("paper_learning.core.daily_pipeline.fetch_arxiv_candidates", return_value=[]) as fetch:
        fetch_recent_candidates_by_group(config, now=now)

    assert fetch.call_count == 8
    first_call = fetch.call_args_list[0].kwargs
    assert first_call["source_group"] == "gpu_graphics"
    assert first_call["categories"] == ["cs.GR", "cs.CV"]
    assert first_call["now"] == now
