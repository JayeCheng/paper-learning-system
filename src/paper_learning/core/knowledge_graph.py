from __future__ import annotations


def build_graph_delta(paper_ids: list[str], concepts: list[str]) -> dict:
    edges = [
        {"source": paper_id, "target": concept, "relation": "related_to", "confidence": 0.5}
        for paper_id in paper_ids
        for concept in concepts
    ]
    nodes = [{"id": concept, "label": concept, "type": "concept", "topics": []} for concept in concepts]
    return {"nodes": nodes, "edges": edges}
