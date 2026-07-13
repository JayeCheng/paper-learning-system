import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from paper_learning.cli import main
from paper_learning.core.models import Paper
from paper_learning.core.state_store import upsert_papers


def _paper() -> Paper:
    return Paper(
        id="arxiv:2601.00001v1",
        title="Status Paper",
        source="arxiv",
        source_type="recent_24h",
        source_group="llm_agent",
        topics=["llm_agent"],
        categories=["cs.CL"],
        url="https://example.com/status",
    )


def test_status_set_persists_and_exports_public_json() -> None:
    cwd = Path.cwd()
    with TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        try:
            upsert_papers([_paper()])

            exit_code = main(
                [
                    "status",
                    "set",
                    "arxiv:2601.00001v1",
                    "--status",
                    "queued",
                    "--priority",
                    "high",
                    "--notes-path",
                    "deep_read/llm_agent/status-paper.md",
                ]
            )

            state = json.loads(Path("data/state/reading_status.json").read_text(encoding="utf-8"))
            public = json.loads(Path("data/public/reading_status.json").read_text(encoding="utf-8"))
            csv_text = Path("data/exports/reading_status.csv").read_text(encoding="utf-8")

            assert exit_code == 0
            assert state["items"]["arxiv:2601.00001v1"]["status"] == "queued"
            assert public["statuses"][0]["priority"] == "high"
            assert "deep_read/llm_agent/status-paper.md" in csv_text
        finally:
            os.chdir(cwd)


def test_status_set_errors_for_unknown_paper() -> None:
    cwd = Path.cwd()
    with TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        try:
            upsert_papers([_paper()])
            exit_code = main(["status", "set", "missing", "--status", "queued"])
        finally:
            os.chdir(cwd)

        assert exit_code == 1
