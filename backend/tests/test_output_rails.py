from src.schemas.landscape import ClusterInfo, LandscapePayload, Relationship
from src.services.guardrails.output_rails import check_output


def _payload(cluster_papers: dict[int, list[str]]) -> LandscapePayload:
    clusters = [
        ClusterInfo(id=i, name=f"C{i}", description="d", paper_ids=pids, centroid=[0.0])
        for i, pids in cluster_papers.items()
    ]
    return LandscapePayload(
        topic="t",
        version=1,
        embedding_model="m",
        extraction_schema_version=1,
        clusters=clusters,
        relationships=[
            Relationship(source_cluster_id=0, target_cluster_id=1, description="r")
        ]
        if len(clusters) > 1
        else [],
        tensions=[],
        open_problems=[],
        paper_versions={pid: 1 for pids in cluster_papers.values() for pid in pids},
    )


def test_clean_payload_passes_untouched():
    payload = _payload({0: ["a", "b"], 1: ["c"]})
    result = check_output(payload, allowed_ids={"a", "b", "c"}, known_ids={"a", "b", "c"})

    assert not result.rejected
    assert result.removed_paper_ids == []
    assert result.payload is payload


def test_single_hallucinated_id_is_stripped():
    payload = _payload({0: ["a", "b", "c", "d", "ghost"], 1: ["e", "f", "g", "h", "i"]})
    valid = {"a", "b", "c", "d", "e", "f", "g", "h", "i"}

    result = check_output(payload, allowed_ids=valid, known_ids=valid)

    assert not result.rejected
    assert result.removed_paper_ids == ["ghost"]
    cluster0 = next(c for c in result.payload.clusters if c.id == 0)
    assert "ghost" not in cluster0.paper_ids
    assert "ghost" not in result.payload.paper_versions


def test_unretrieved_but_real_paper_is_also_stripped():
    payload = _payload({0: ["a", "b", "c", "d", "sneaky"], 1: ["e", "f", "g", "h", "i"]})
    known = {"a", "b", "c", "d", "e", "f", "g", "h", "i", "sneaky"}  # exists in db
    allowed = known - {"sneaky"}  # but was never retrieved for this topic

    result = check_output(payload, allowed_ids=allowed, known_ids=known)

    assert result.removed_paper_ids == ["sneaky"]


def test_emptied_cluster_and_its_relationships_are_dropped():
    payload = _payload({0: ["ghost1", "ghost2"], 1: ["a", "b", "c", "d", "e", "f", "g", "h"]})
    valid = {"a", "b", "c", "d", "e", "f", "g", "h"}

    result = check_output(payload, allowed_ids=valid, known_ids=valid)

    assert not result.rejected
    assert [c.id for c in result.payload.clusters] == [1]
    assert result.payload.relationships == []  # referenced the dropped cluster


def test_excessive_hallucination_rejects_payload():
    payload = _payload({0: ["ghost1", "ghost2", "ghost3"], 1: ["a", "b"]})
    valid = {"a", "b"}

    result = check_output(payload, allowed_ids=valid, known_ids=valid)

    assert result.rejected
    assert "60%" in result.reason


def test_empty_citation_list_rejects():
    payload = _payload({})
    result = check_output(payload, allowed_ids={"a"}, known_ids={"a"})
    assert result.rejected
