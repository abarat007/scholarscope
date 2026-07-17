"""Pure transformation from a stored landscape payload to the reading-map graph."""

from src.schemas.landscape import GraphEdge, GraphNode, LandscapeGraph, LandscapePayload


def build_graph(payload: LandscapePayload, titles: dict[str, str]) -> LandscapeGraph:
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    for cluster in payload.clusters:
        nodes.append(
            GraphNode(
                id=f"cluster:{cluster.id}",
                type="cluster",
                label=cluster.name,
                cluster_id=cluster.id,
            )
        )
        for paper_id in cluster.paper_ids:
            nodes.append(
                GraphNode(
                    id=paper_id,
                    type="paper",
                    label=titles.get(paper_id, paper_id),
                    cluster_id=cluster.id,
                    added_in_version=payload.paper_versions.get(paper_id),
                )
            )
            edges.append(
                GraphEdge(source=f"cluster:{cluster.id}", target=paper_id, type="membership")
            )

    for rel in payload.relationships:
        edges.append(
            GraphEdge(
                source=f"cluster:{rel.source_cluster_id}",
                target=f"cluster:{rel.target_cluster_id}",
                type="relationship",
                label=rel.description,
            )
        )

    return LandscapeGraph(
        topic=payload.topic,
        version=payload.version,
        paper_count=len(payload.paper_versions),
        nodes=nodes,
        edges=edges,
        tensions=payload.tensions,
        open_problems=payload.open_problems,
    )
