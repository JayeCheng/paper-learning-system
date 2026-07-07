from __future__ import annotations

from paper_learning.core.models import DailyReport


def render_daily_markdown(report: DailyReport) -> str:
    lines = [
        f"# Paper Radar - {report.date}",
        "",
        f"Generated: {report.generated_at}",
        "",
        "## Executive Summary",
        "",
        report.summary,
        "",
        "## Top Papers",
        "",
    ]

    if report.papers:
        for index, paper in enumerate(report.papers, start=1):
            topics = ", ".join(paper.topics)
            lines.append(f"{index}. [{paper.title}]({paper.url})")
            lines.append(f"   - Source: {paper.source}")
            lines.append(f"   - Source type: {paper.source_type or 'unspecified'}")
            lines.append(f"   - Level: {paper.recommendation_level or 'unrated'}")
            lines.append(f"   - Score: {paper.score if paper.score is not None else 'n/a'}")
            lines.append(f"   - Topics: {topics}")
            if paper.why_recommended:
                lines.append(f"   - Why: {paper.why_recommended}")
    else:
        lines.append("No papers selected yet.")

    lines.extend(
        [
            "",
            "## S-Level Deep Read Candidate",
            "",
            ", ".join(report.s_level_candidate_ids) if report.s_level_candidate_ids else "None selected.",
            "",
            "## Knowledge Graph Delta",
            "",
        ]
    )

    lines.extend(report.knowledge_graph_delta or ["No graph updates yet."])
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- {action}" for action in report.next_actions)
    lines.append("")
    return "\n".join(lines)
