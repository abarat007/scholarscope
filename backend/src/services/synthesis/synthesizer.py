"""Cross-paper landscape synthesis: cluster extractions, then LLM-describe.

One LLM call per cluster (name + description) and one cross-cluster call
(relationships, tensions, open problems) — LLM cost scales with cluster
count, not paper count.
"""

import asyncio
import re

from src.config import get_settings
from src.schemas.extraction import EXTRACTION_SCHEMA_VERSION, PaperExtraction
from src.schemas.landscape import (
    ClusterDescription,
    ClusterInfo,
    CrossClusterAnalysis,
    LandscapePayload,
)
from src.schemas.paper import ArxivPaper
from src.services.llm.client import LLMUsage, StructuredLLM
from src.services.retrieval.embeddings import EmbeddingService
from src.services.synthesis.clustering import cluster_vectors

CLUSTER_SYSTEM_PROMPT = (
    "You are mapping a research field. Given structured extractions of papers "
    "that clustered together, produce a specific, technical name and a faithful "
    "description of what unites them. Never invent papers or claims."
)

CROSS_CLUSTER_SYSTEM_PROMPT = (
    "You are analyzing the structure of a research field organized into "
    "clusters. Identify real relationships between clusters, genuine tensions "
    "or disagreements, and concrete open problems. The integer id given for "
    "each cluster is only for populating source_cluster_id/target_cluster_id "
    "on relationships — never write a bare id or the phrase 'cluster N' in "
    "prose. In tensions, open_problems, and relationship descriptions, refer "
    "to a cluster by its exact quoted name, e.g. \"Cross-Encoder Reranking\", "
    "so a reader never has to resolve a number. Never invent clusters, "
    "papers, or results."
)

MAX_PAPERS_PER_CLUSTER_PROMPT = 15


def extraction_embedding_text(title: str, extraction: PaperExtraction) -> str:
    """What gets embedded for clustering: the paper's conceptual signature."""
    return "\n".join([title, extraction.problem, extraction.method, extraction.contribution])


def _cluster_prompt(
    topic: str, members: list[tuple[ArxivPaper, PaperExtraction]]
) -> str:
    lines = [f"Topic under study: {topic}", "", "Papers in this cluster:"]
    for paper, ex in members[:MAX_PAPERS_PER_CLUSTER_PROMPT]:
        lines.append(f"- {paper.title}")
        lines.append(f"  problem: {ex.problem}")
        lines.append(f"  contribution: {ex.contribution}")
    if len(members) > MAX_PAPERS_PER_CLUSTER_PROMPT:
        lines.append(f"...and {len(members) - MAX_PAPERS_PER_CLUSTER_PROMPT} more papers.")
    return "\n".join(lines)


def _cross_cluster_prompt(topic: str, clusters: list[ClusterInfo]) -> str:
    lines = [f"Topic under study: {topic}", "", "Clusters:"]
    for c in clusters:
        lines.append(f"- id={c.id} name={c.name}: {c.description}")
    return "\n".join(lines)


async def describe_cluster(
    llm: StructuredLLM,
    topic: str,
    members: list[tuple[ArxivPaper, PaperExtraction]],
    usage: LLMUsage,
) -> ClusterDescription:
    result = await llm.parse(
        system=CLUSTER_SYSTEM_PROMPT,
        user=_cluster_prompt(topic, members),
        schema=ClusterDescription,
        max_tokens=800,
    )
    usage.add(result.usage)
    description = result.output
    assert isinstance(description, ClusterDescription)
    return description


_CLUSTER_ID_RE_TEMPLATE = r"\bcluster\s*#?\s*{id}\b"


def _normalize_cluster_references(text: str, clusters: list[ClusterInfo]) -> str:
    """Rewrite any leftover 'cluster N' (0-indexed id) into the cluster's name.

    Defense in depth: the prompt asks the model to use names, not ids, but
    structured-output models don't always comply. A reader should never have
    to mentally resolve a bare number against the UI's 1-indexed labels.
    """
    for cluster in clusters:
        pattern = re.compile(_CLUSTER_ID_RE_TEMPLATE.format(id=cluster.id), re.IGNORECASE)
        text = pattern.sub(f'"{cluster.name}"', text)
    return text


async def analyze_cross_cluster(
    llm: StructuredLLM, topic: str, clusters: list[ClusterInfo], usage: LLMUsage
) -> CrossClusterAnalysis:
    result = await llm.parse(
        system=CROSS_CLUSTER_SYSTEM_PROMPT,
        user=_cross_cluster_prompt(topic, clusters),
        schema=CrossClusterAnalysis,
        max_tokens=3000,
    )
    usage.add(result.usage)
    analysis = result.output
    assert isinstance(analysis, CrossClusterAnalysis)
    valid_ids = {c.id for c in clusters}
    analysis.relationships = [
        r
        for r in analysis.relationships
        if r.source_cluster_id in valid_ids
        and r.target_cluster_id in valid_ids
        and r.source_cluster_id != r.target_cluster_id
    ]
    for r in analysis.relationships:
        r.description = _normalize_cluster_references(r.description, clusters)
    analysis.tensions = [_normalize_cluster_references(t, clusters) for t in analysis.tensions]
    analysis.open_problems = [
        _normalize_cluster_references(p, clusters) for p in analysis.open_problems
    ]
    return analysis


async def build_landscape(
    topic: str,
    papers: list[ArxivPaper],
    extractions: dict[str, PaperExtraction],
    *,
    embedder: EmbeddingService,
    llm: StructuredLLM,
    usage: LLMUsage,
    version: int = 1,
    paper_versions: dict[str, int] | None = None,
) -> LandscapePayload:
    """Cluster the papers and synthesize a full landscape from scratch."""
    texts = [extraction_embedding_text(p.title, extractions[p.arxiv_id]) for p in papers]
    vectors = await asyncio.to_thread(embedder.embed_passages, texts)
    labels, centroids = cluster_vectors(vectors)

    clusters: list[ClusterInfo] = []
    for cluster_id in range(len(centroids)):
        members = [
            (p, extractions[p.arxiv_id])
            for p, label in zip(papers, labels, strict=True)
            if label == cluster_id
        ]
        described = await describe_cluster(llm, topic, members, usage)
        clusters.append(
            ClusterInfo(
                id=cluster_id,
                name=described.name,
                description=described.description,
                paper_ids=[p.arxiv_id for p, _ in members],
                centroid=centroids[cluster_id],
            )
        )

    analysis = await analyze_cross_cluster(llm, topic, clusters, usage)
    return LandscapePayload(
        topic=topic,
        version=version,
        embedding_model=get_settings().embedding_model,
        extraction_schema_version=EXTRACTION_SCHEMA_VERSION,
        clusters=clusters,
        relationships=analysis.relationships,
        tensions=analysis.tensions,
        open_problems=analysis.open_problems,
        paper_versions=paper_versions or {p.arxiv_id: version for p in papers},
    )
