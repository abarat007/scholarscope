from datetime import UTC, datetime

from src.schemas.extraction import PaperExtraction
from src.schemas.landscape import (
    ClusterDescription,
    ClusterInfo,
    CrossClusterAnalysis,
    Relationship,
)
from src.services.llm.client import LLMResult, LLMUsage
from src.services.synthesis.synthesizer import (
    _normalize_cluster_references,
    analyze_cross_cluster,
    build_landscape,
)


def _paper_and_extraction(suffix: str, theme: str):
    from src.schemas.paper import ArxivPaper

    now = datetime(2026, 1, 1, tzinfo=UTC)
    paper = ArxivPaper(
        arxiv_id=f"2601.{suffix}",
        version=1,
        title=f"{theme} paper {suffix}",
        abstract=f"About {theme}.",
        authors=["A"],
        categories=["cs.CL"],
        primary_category="cs.CL",
        published_at=now,
        updated_at=now,
        pdf_url="https://example.org",
    )
    extraction = PaperExtraction(
        problem=f"{theme} problem",
        method=f"{theme} method",
        results="results",
        contribution=f"{theme} contribution",
        limitations="not stated",
        key_terms=[theme],
    )
    return paper, extraction


class QueueEmbedder:
    """Returns preset vectors in call order — deterministic clustering."""

    def __init__(self, vectors: list[list[float]]):
        self._vectors = vectors

    def embed_passages(self, texts):
        assert len(texts) == len(self._vectors)
        return self._vectors


class ScriptedLLM:
    """Names clusters sequentially; returns a fixed cross-cluster analysis."""

    def __init__(self, cross: CrossClusterAnalysis):
        self.cluster_calls = 0
        self.cross = cross

    async def parse(self, *, system, user, schema, max_tokens=2000):
        usage = LLMUsage(500, 100)
        if schema is ClusterDescription:
            self.cluster_calls += 1
            return LLMResult(
                output=ClusterDescription(
                    name=f"Cluster {self.cluster_calls}",
                    description=f"Description {self.cluster_calls}",
                ),
                usage=usage,
            )
        assert schema is CrossClusterAnalysis
        return LLMResult(output=self.cross, usage=usage)


async def test_build_landscape_clusters_and_synthesizes():
    pairs = [
        _paper_and_extraction("00001", "retrieval"),
        _paper_and_extraction("00002", "retrieval"),
        _paper_and_extraction("00003", "agents"),
        _paper_and_extraction("00004", "agents"),
    ]
    papers = [p for p, _ in pairs]
    extractions = {p.arxiv_id: e for p, e in pairs}
    # two obvious groups in embedding space
    embedder = QueueEmbedder([[1, 0], [0.99, 0.01], [0, 1], [0.01, 0.99]])
    cross = CrossClusterAnalysis(
        relationships=[
            Relationship(source_cluster_id=0, target_cluster_id=1, description="feeds into"),
            Relationship(source_cluster_id=5, target_cluster_id=0, description="bogus id"),
            Relationship(source_cluster_id=1, target_cluster_id=1, description="self loop"),
        ],
        tensions=["speed vs quality"],
        open_problems=["evaluation"],
    )
    llm = ScriptedLLM(cross)
    usage = LLMUsage()

    payload = await build_landscape(
        "test topic", papers, extractions, embedder=embedder, llm=llm, usage=usage
    )

    assert len(payload.clusters) == 2
    assert llm.cluster_calls == 2
    # each cluster holds exactly the two papers of one theme
    memberships = sorted(sorted(c.paper_ids) for c in payload.clusters)
    assert memberships == [["2601.00001", "2601.00002"], ["2601.00003", "2601.00004"]]
    # hallucinated / self-loop relationships filtered out
    assert payload.relationships == [
        Relationship(source_cluster_id=0, target_cluster_id=1, description="feeds into")
    ]
    assert payload.paper_versions == {p.arxiv_id: 1 for p in papers}
    # usage accumulated: 2 cluster calls + 1 cross call
    assert usage.input_tokens == 1500


def _cluster(id_: int, name: str) -> ClusterInfo:
    return ClusterInfo(id=id_, name=name, description="d", paper_ids=[], centroid=[0.0])


def test_normalize_rewrites_bare_cluster_id_to_quoted_name():
    clusters = [_cluster(0, "Cross-Encoder Reranking"), _cluster(1, "Mismatched Cluster")]

    text = "The inclusion of cluster 1 highlights a mismatch with cluster 0's focus."

    normalized = _normalize_cluster_references(text, clusters)

    assert normalized == (
        'The inclusion of "Mismatched Cluster" highlights a mismatch '
        'with "Cross-Encoder Reranking"\'s focus.'
    )


def test_normalize_is_case_insensitive_and_handles_hash_or_no_space():
    clusters = [_cluster(2, "Spatial Omics Integration")]
    text = "See Cluster #2 and cluster2's papers."

    normalized = _normalize_cluster_references(text, clusters)

    assert normalized.count('"Spatial Omics Integration"') == 2


def test_normalize_leaves_unrelated_text_untouched():
    clusters = [_cluster(0, "A"), _cluster(1, "B")]
    text = "No numeric cluster references here."

    assert _normalize_cluster_references(text, clusters) == text


async def test_analyze_cross_cluster_normalizes_tensions_and_open_problems():
    clusters = [_cluster(0, "Cross-Encoder Reranking"), _cluster(1, "Mismatched Cluster")]

    class NumericLLM:
        async def parse(self, *, system, user, schema, max_tokens=2000):
            return LLMResult(
                output=CrossClusterAnalysis(
                    relationships=[
                        Relationship(
                            source_cluster_id=0,
                            target_cluster_id=1,
                            description="cluster 0 informs cluster 1",
                        )
                    ],
                    tensions=["cluster 1 conflates unrelated fields"],
                    open_problems=["cluster 0 lacks a benchmark"],
                ),
                usage=LLMUsage(10, 5),
            )

    analysis = await analyze_cross_cluster(NumericLLM(), "topic", clusters, LLMUsage())

    assert analysis.relationships[0].description == (
        '"Cross-Encoder Reranking" informs "Mismatched Cluster"'
    )
    assert analysis.tensions == ['"Mismatched Cluster" conflates unrelated fields']
    assert analysis.open_problems == ['"Cross-Encoder Reranking" lacks a benchmark']
