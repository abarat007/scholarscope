from datetime import UTC, datetime

import pytest
from src.schemas.extraction import PaperExtraction
from src.schemas.landscape import (
    ClusterDescription,
    ClusterInfo,
    CrossClusterAnalysis,
    LandscapePayload,
)
from src.schemas.paper import ArxivPaper
from src.services.llm.client import LLMResult, LLMUsage
from src.services.synthesis.merge import merge_landscape


def _paper(pid: str) -> ArxivPaper:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    return ArxivPaper(
        arxiv_id=pid,
        version=1,
        title=f"Paper {pid}",
        abstract="abstract",
        authors=["A"],
        categories=["cs.CL"],
        primary_category="cs.CL",
        published_at=now,
        updated_at=now,
        pdf_url="https://example.org",
    )


def _extraction(pid: str) -> PaperExtraction:
    return PaperExtraction(
        problem=f"problem {pid}",
        method="method",
        results="results",
        contribution="contribution",
        limitations="not stated",
        key_terms=["term"],
    )


def _payload(paper_versions: dict[str, int], clusters: list[ClusterInfo]) -> LandscapePayload:
    return LandscapePayload(
        topic="rag",
        version=1,
        embedding_model="test",
        extraction_schema_version=1,
        clusters=clusters,
        relationships=[],
        tensions=["old tension"],
        open_problems=["old problem"],
        paper_versions=paper_versions,
    )


class QueueEmbedder:
    def __init__(self, vectors):
        self._vectors = list(vectors)

    def embed_passages(self, texts):
        assert len(texts) == len(self._vectors)
        return self._vectors


class CountingLLM:
    def __init__(self):
        self.cluster_calls = 0
        self.cross_calls = 0

    async def parse(self, *, system, user, schema, max_tokens=2000):
        usage = LLMUsage(100, 20)
        if schema is ClusterDescription:
            self.cluster_calls += 1
            return LLMResult(
                output=ClusterDescription(name=f"Renamed {self.cluster_calls}", description="d"),
                usage=usage,
            )
        assert schema is CrossClusterAnalysis
        self.cross_calls += 1
        return LLMResult(
            output=CrossClusterAnalysis(
                relationships=[], tensions=["new tension"], open_problems=["new problem"]
            ),
            usage=usage,
        )


BASE_CLUSTERS = [
    ClusterInfo(id=0, name="A", description="da", paper_ids=["e1", "e2"], centroid=[1.0, 0.0]),
    ClusterInfo(id=1, name="B", description="db", paper_ids=["e3"], centroid=[0.0, 1.0]),
]


async def test_no_new_papers_is_a_noop():
    payload = _payload({"e1": 1, "e2": 1, "e3": 1}, BASE_CLUSTERS)
    result, added, rebuilt = await merge_landscape(
        payload,
        [_paper("e1")],
        {"e1": _extraction("e1")},
        embedder=QueueEmbedder([]),
        llm=CountingLLM(),
        usage=LLMUsage(),
    )
    assert (added, rebuilt) == (0, False)
    assert result is payload


async def test_near_papers_join_cluster_and_only_dirty_cluster_renamed():
    existing = {f"e{i}": 1 for i in range(1, 11)}  # 10 existing papers
    clusters = [
        ClusterInfo(
            id=0, name="A", description="da",
            paper_ids=[f"e{i}" for i in range(1, 8)], centroid=[1.0, 0.0],
        ),
        ClusterInfo(
            id=1, name="B", description="db",
            paper_ids=["e8", "e9", "e10"], centroid=[0.0, 1.0],
        ),
    ]
    payload = _payload(existing, clusters)
    llm = CountingLLM()
    # two new papers, both close to cluster 0
    new = [_paper("n1"), _paper("n2")]
    extractions = {p.arxiv_id: _extraction(p.arxiv_id) for p in new}
    extractions.update({pid: _extraction(pid) for pid in existing})

    result, added, rebuilt = await merge_landscape(
        payload,
        new,
        extractions,
        embedder=QueueEmbedder([[0.95, 0.05], [0.9, 0.1]]),
        llm=llm,
        usage=LLMUsage(),
    )

    assert (added, rebuilt) == (2, False)
    assert result.version == 2
    cluster0 = next(c for c in result.clusters if c.id == 0)
    cluster1 = next(c for c in result.clusters if c.id == 1)
    assert {"n1", "n2"} <= set(cluster0.paper_ids)
    assert cluster0.name.startswith("Renamed")  # dirty -> renamed
    assert cluster1.name == "B"  # untouched cluster keeps its identity
    assert llm.cluster_calls == 1
    assert llm.cross_calls == 1  # structure changed -> cross analysis re-ran
    assert result.paper_versions["n1"] == 2
    assert result.paper_versions["e1"] == 1


async def test_outlier_group_spawns_new_cluster():
    existing = {f"e{i}": 1 for i in range(1, 11)}
    payload = _payload(existing, [c.model_copy(deep=True) for c in BASE_CLUSTERS])
    payload.clusters[0].paper_ids = [f"e{i}" for i in range(1, 8)]
    payload.clusters[1].paper_ids = ["e8", "e9", "e10"]
    llm = CountingLLM()
    # three new papers pointing in a genuinely new direction
    new = [_paper("n1"), _paper("n2"), _paper("n3")]
    extractions = {p.arxiv_id: _extraction(p.arxiv_id) for p in new}

    result, added, rebuilt = await merge_landscape(
        payload,
        new,
        extractions,
        embedder=QueueEmbedder([[-1.0, 0.0], [-0.98, -0.02], [-0.99, 0.01]]),
        llm=llm,
        usage=LLMUsage(),
    )

    assert (added, rebuilt) == (3, False)
    assert len(result.clusters) == 3
    new_cluster = next(c for c in result.clusters if c.id == 2)
    assert sorted(new_cluster.paper_ids) == ["n1", "n2", "n3"]
    assert result.tensions == ["new tension"]  # cross analysis re-ran


async def test_large_influx_triggers_full_rebuild():
    existing = {"e1": 1, "e2": 1}
    payload = _payload(existing, [c.model_copy(deep=True) for c in BASE_CLUSTERS])
    llm = CountingLLM()
    new = [_paper(f"n{i}") for i in range(1, 5)]  # 4 new vs 2 existing -> rebuild
    extractions = {p.arxiv_id: _extraction(p.arxiv_id) for p in new}
    extractions.update({pid: _extraction(pid) for pid in existing})

    # rebuild embeds only the retrieved new papers present in papers list
    result, added, rebuilt = await merge_landscape(
        payload,
        new,
        extractions,
        embedder=QueueEmbedder([[1, 0], [0.99, 0.01], [0, 1], [0.01, 0.99]]),
        llm=llm,
        usage=LLMUsage(),
    )

    assert rebuilt is True
    assert added == 4
    assert result.version == 2
    # history preserved across rebuild
    assert result.paper_versions["e1"] == 1
    assert result.paper_versions["n1"] == 2


async def test_lone_outlier_attaches_to_nearest_cluster():
    existing = {f"e{i}": 1 for i in range(1, 11)}
    payload = _payload(existing, [c.model_copy(deep=True) for c in BASE_CLUSTERS])
    payload.clusters[0].paper_ids = [f"e{i}" for i in range(1, 8)]
    payload.clusters[1].paper_ids = ["e8", "e9", "e10"]
    new = [_paper("n1")]
    extractions = {"n1": _extraction("n1")}

    result, added, rebuilt = await merge_landscape(
        payload,
        new,
        extractions,
        embedder=QueueEmbedder([[-0.5, 0.5]]),  # below threshold everywhere
        llm=CountingLLM(),
        usage=LLMUsage(),
    )

    assert (added, rebuilt) == (1, False)
    assert len(result.clusters) == 2  # no new cluster for a single outlier
    assert any("n1" in c.paper_ids for c in result.clusters)


@pytest.mark.parametrize("threshold_vector", [[0.95, 0.05]])
async def test_centroid_moves_toward_new_member(threshold_vector):
    existing = {f"e{i}": 1 for i in range(1, 11)}
    payload = _payload(existing, [c.model_copy(deep=True) for c in BASE_CLUSTERS])
    payload.clusters[0].paper_ids = [f"e{i}" for i in range(1, 8)]
    payload.clusters[1].paper_ids = ["e8", "e9", "e10"]

    result, _, _ = await merge_landscape(
        payload,
        [_paper("n1")],
        {"n1": _extraction("n1")},
        embedder=QueueEmbedder([threshold_vector]),
        llm=CountingLLM(),
        usage=LLMUsage(),
    )

    cluster0 = next(c for c in result.clusters if c.id == 0)
    # running mean of 7 members at [1,0] plus one at [0.95,0.05]
    assert cluster0.centroid[0] == pytest.approx((7 * 1.0 + 0.95) / 8)
    assert cluster0.centroid[1] == pytest.approx(0.05 / 8)
