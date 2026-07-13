from pathlib import Path


def test_daily_workflow_has_stable_commit_and_push_contract() -> None:
    workflow = Path(".github/workflows/daily-paper-radar.yml").read_text(encoding="utf-8")

    assert "contents: write" in workflow
    assert "concurrency:" in workflow
    assert 'cron: "10 22 * * *"' in workflow
    assert "workflow_dispatch:" in workflow
    assert "git diff --cached --quiet" in workflow
    assert "chore: update daily paper radar ${REPORT_DATE}" in workflow
    assert "git push origin HEAD:${GITHUB_REF_NAME}" in workflow
