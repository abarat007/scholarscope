"""Incremental landscape growth.

Re-running a topic merges new papers into the existing landscape instead of
rebuilding it, keeping cluster identity (and the UI) stable:

1. New papers whose embedding is within ASSIGN_THRESHOLD cosine of an existing
   centroid join that cluster; the centroid updates as a running mean and the
   cluster is marked dirty (re-described by the LLM).
2. Outliers form new clusters (silhouette k-means among themselves) when there
   are at least MIN_NEW_CLUSTER_SIZE of them; fewer than that, each joins its
   nearest cluster regardless of threshold so no paper is orphaned.
3. If new papers exceed REBUILD_FRACTION of the grown corpus, cluster identity
   is stale anyway — do a full rebuild, preserving paper_versions history.
4. Cross-cluster analysis re-runs only when cluster structure changed.
"""

import asyncio

from src.schemas.extraction import PaperExtraction
from src.schemas.landscape import ClusterInfo, LandscapePayload
from src.schemas.paper import ArxivPaper
from src.services.llm.client import LLMUsage, StructuredLLM
from src.services.retrieval.embeddings import EmbeddingService
from src.services.synthesis.clustering import cluster_vectors, cosine_similarity
from src.services.synthesis.synthesizer import (
    analyze_cross_cluster,
    build_landscape,
    describe_cluster,
    extraction_embedding_text,
)

ASSIGN_THRESHOLD = 0.6
REBUILD_FRACTION = 0.3
MIN_NEW_CLUSTER_SIZE = 3


def _update_centroid(centroid: list[float], size: int, vector: list[float]) -> list[float]:
    """Running mean update after adding one member to a cluster of `size`."""
    return [(c * size + v) / (size + 1) for c, v in zip(centroid, vector, strict=True)]


async def merge_landscape(
    existing: LandscapePayload,
    papers: list[ArxivPaper],
    extractions: dict[str, PaperExtraction],
    *,
    embedder: EmbeddingService,
    llm: StructuredLLM,
    usage: LLMUsage,
) -> tuple[LandscapePayload, int, bool]:
    """Merge newly retrieved papers into an existing landscape.

    Returns (payload, new_paper_count, rebuilt).
    """
    papers_by_id = {p.arxiv_id: p for p in papers}
    new_papers = [p for p in papers if p.arxiv_id not in existing.paper_versions]
    if not new_papers:
        return existing, 0, False

    next_version = existing.version + 1
    total_after = len(existing.paper_versions) + len(new_papers)

    if len(new_papers) / total_after > REBUILD_FRACTION:
        # Too much new material for the old structure to stay meaningful.
        paper_versions = dict(existing.paper_versions)
        for p in new_papers:
            paper_versions[p.arxiv_id] = next_version
        known_ids = set(paper_versions)
        rebuilt = await build_landscape(
            existing.topic,
            [p for pid, p in papers_by_id.items() if pid in known_ids],
            extractions,
            embedder=embedder,
            llm=llm,
            usage=usage,
            version=next_version,
            paper_versions=paper_versions,
        )
        return rebuilt, len(new_papers), True

    texts = [extraction_embedding_text(p.title, extractions[p.arxiv_id]) for p in new_papers]
    vectors = await asyncio.to_thread(embedder.embed_passages, texts)

    clusters = [c.model_copy(deep=True) for c in existing.clusters]
    dirty: set[int] = set()
    outliers: list[tuple[ArxivPaper, list[float]]] = []

    def nearest(vector: list[float]) -> tuple[int, float]:
        scored = [(i, cosine_similarity(vector, c.centroid)) for i, c in enumerate(clusters)]
        return max(scored, key=lambda item: item[1])

    for paper, vector in zip(new_papers, vectors, strict=True):
        index, similarity = nearest(vector)
        if similarity >= ASSIGN_THRESHOLD:
            cluster = clusters[index]
            cluster.centroid = _update_centroid(
                cluster.centroid, len(cluster.paper_ids), vector
            )
            cluster.paper_ids.append(paper.arxiv_id)
            dirty.add(cluster.id)
        else:
            outliers.append((paper, vector))

    if outliers:
        if len(outliers) >= MIN_NEW_CLUSTER_SIZE:
            labels, centroids = cluster_vectors([v for _, v in outliers])
            next_id = max(c.id for c in clusters) + 1
            for new_index, centroid in enumerate(centroids):
                members = [p for (p, _), label in zip(outliers, labels, strict=True)
                           if label == new_index]
                described = await describe_cluster(
                    llm,
                    existing.topic,
                    [(p, extractions[p.arxiv_id]) for p in members],
                    usage,
                )
                clusters.append(
                    ClusterInfo(
                        id=next_id + new_index,
                        name=described.name,
                        description=described.description,
                        paper_ids=[p.arxiv_id for p in members],
                        centroid=centroid,
                    )
                )
        else:
            # Too few to justify a cluster: attach to nearest so nothing orphans.
            for paper, vector in outliers:
                index, _ = nearest(vector)
                cluster = clusters[index]
                cluster.centroid = _update_centroid(
                    cluster.centroid, len(cluster.paper_ids), vector
                )
                cluster.paper_ids.append(paper.arxiv_id)
                dirty.add(cluster.id)

    # Re-describe only clusters whose membership changed.
    for cluster in clusters:
        if cluster.id in dirty:
            members = [
                (papers_by_id[pid], extractions[pid])
                for pid in cluster.paper_ids
                if pid in papers_by_id and pid in extractions
            ]
            if members:
                described = await describe_cluster(llm, existing.topic, members, usage)
                cluster.name = described.name
                cluster.description = described.description

    structure_changed = bool(dirty) or len(clusters) != len(existing.clusters)
    if structure_changed:
        analysis = await analyze_cross_cluster(llm, existing.topic, clusters, usage)
        relationships = analysis.relationships
        tensions = analysis.tensions
        open_problems = analysis.open_problems
    else:
        relationships = existing.relationships
        tensions = existing.tensions
        open_problems = existing.open_problems

    paper_versions = dict(existing.paper_versions)
    for p in new_papers:
        paper_versions[p.arxiv_id] = next_version

    payload = existing.model_copy(
        update={
            "version": next_version,
            "clusters": clusters,
            "relationships": relationships,
            "tensions": tensions,
            "open_problems": open_problems,
            "paper_versions": paper_versions,
        }
    )
    return payload, len(new_papers), False
