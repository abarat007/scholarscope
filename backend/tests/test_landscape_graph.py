from src.schemas.landscape import ClusterInfo, LandscapePayload, Relationship
from src.services.synthesis.graph import build_graph


def _payload() -> LandscapePayload:
    return LandscapePayload(
        topic="rag",
        version=2,
        embedding_model="test-model",
        extraction_schema_version=1,
        clusters=[
            ClusterInfo(
                id=0, name="Rerankers", description="d0", paper_ids=["p1", "p2"], centroid=[1, 0]
            ),
            ClusterInfo(id=1, name="Agents", description="d1", paper_ids=["p3"], centroid=[0, 1]),
        ],
        relationships=[
            Relationship(source_cluster_id=0, target_cluster_id=1, description="informs")
        ],
        tensions=["latency vs quality"],
        open_problems=["evaluation"],
        paper_versions={"p1": 1, "p2": 2, "p3": 1},
    )


def test_graph_has_cluster_and_paper_nodes_with_membership_edges():
    graph = build_graph(_payload(), {"p1": "Paper One", "p2": "Paper Two", "p3": "Paper Three"})

    node_ids = {n.id for n in graph.nodes}
    assert node_ids == {"cluster:0", "cluster:1", "p1", "p2", "p3"}

    memberships = [(e.source, e.target) for e in graph.edges if e.type == "membership"]
    assert ("cluster:0", "p1") in memberships
    assert ("cluster:1", "p3") in memberships

    relationships = [e for e in graph.edges if e.type == "relationship"]
    assert len(relationships) == 1
    assert relationships[0].label == "informs"


def test_graph_carries_versions_and_labels():
    graph = build_graph(_payload(), {"p1": "Paper One"})

    p1 = next(n for n in graph.nodes if n.id == "p1")
    p2 = next(n for n in graph.nodes if n.id == "p2")
    assert p1.label == "Paper One"
    assert p1.added_in_version == 1
    assert p2.added_in_version == 2  # "new since last visit" signal
    assert p2.label == "p2"  # falls back to id when title unknown
    assert graph.paper_count == 3
    assert graph.tensions == ["latency vs quality"]
