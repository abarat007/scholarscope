from datetime import UTC, datetime

from src.schemas.extraction import PaperExtraction
from src.schemas.landscape import ClusterDescription, CrossClusterAnalysis, Relationship
from src.services.llm.client import LLMResult, LLMUsage
from src.services.synthesis.synthesizer import build_landscape


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
