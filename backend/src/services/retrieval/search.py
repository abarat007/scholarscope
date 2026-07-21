"""Retrieval over the papers index.

Query builders are pure functions returning OpenSearch request bodies, so the
exact BM25/k-NN DSL is unit-testable and visible in one place.
"""

import asyncio
import logging
from datetime import date

from src.schemas.query_optimization import OptimizedQuery
from src.schemas.search import SearchHit
from src.services.ingestion.chunking import paper_chunk
from src.services.llm.client import get_llm
from src.services.retrieval.embeddings import get_embedding_service
from src.services.retrieval.fusion import reciprocal_rank_fusion
from src.services.retrieval.indexing import INDEX_NAME
from src.services.retrieval.os_client import get_os_client
from src.services.retrieval.query_optimizer import optimize_query
from src.services.retrieval.reranker import get_reranker

log = logging.getLogger(__name__)

SOURCE_FIELDS = ["arxiv_id", "title", "abstract", "primary_category", "published_at"]


async def _try_optimize(q: str) -> OptimizedQuery | None:
    """Best-effort query optimization. Never breaks search — on any failure
    (no API key, rate limit, provider outage) we fall back to the plain query
    rather than degrading a feature that otherwise needs no LLM at all."""
    try:
        return await optimize_query(q, get_llm())
    except Exception:
        log.warning("query optimization failed; using the unoptimized query", exc_info=True)
        return None


def build_filters(
    category: str | None = None,
    published_from: date | None = None,
    published_to: date | None = None,
) -> list[dict]:
    filters: list[dict] = []
    if category:
        filters.append({"term": {"categories": category}})
    if published_from or published_to:
        bounds: dict[str, str] = {}
        if published_from:
            bounds["gte"] = published_from.isoformat()
        if published_to:
            bounds["lte"] = published_to.isoformat()
        filters.append({"range": {"published_at": bounds}})
    return filters


def build_bm25_query(
    q: str,
    *,
    k: int,
    category: str | None = None,
    published_from: date | None = None,
    published_to: date | None = None,
) -> dict:
    return {
        "size": k,
        "_source": SOURCE_FIELDS,
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": q,
                            "fields": ["title^2", "abstract"],
                        }
                    }
                ],
                "filter": build_filters(category, published_from, published_to),
            }
        },
    }


def parse_hits(response_body: dict) -> list[SearchHit]:
    return [
        SearchHit(score=hit["_score"], **hit["_source"])
        for hit in response_body["hits"]["hits"]
    ]


def build_knn_query(
    vector: list[float],
    *,
    k: int,
    category: str | None = None,
    published_from: date | None = None,
    published_to: date | None = None,
) -> dict:
    knn: dict = {"vector": vector, "k": k}
    filters = build_filters(category, published_from, published_to)
    if filters:
        # lucene-engine k-NN supports efficient pre-filtering
        knn["filter"] = {"bool": {"filter": filters}}
    return {
        "size": k,
        "_source": SOURCE_FIELDS,
        "query": {"knn": {"embedding": knn}},
    }


async def dense_search(
    q: str,
    *,
    k: int = 10,
    optimize: bool = False,
    category: str | None = None,
    published_from: date | None = None,
    published_to: date | None = None,
    _optimized: OptimizedQuery | None = None,
) -> list[SearchHit]:
    """Dense k-NN search. With optimize=True, embeds a HyDE hypothetical
    passage instead of the bare query — see query_optimizer.py."""
    if _optimized is None and optimize:
        _optimized = await _try_optimize(q)

    if _optimized is not None:
        embedder = get_embedding_service()
        vector = (await asyncio.to_thread(embedder.embed_passages, [_optimized.hyde_passage]))[0]
    else:
        vector = await asyncio.to_thread(get_embedding_service().embed_query, q)

    body = build_knn_query(
        vector, k=k, category=category, published_from=published_from, published_to=published_to
    )
    resp = await get_os_client().post(f"/{INDEX_NAME}/_search", json=body)
    resp.raise_for_status()
    return parse_hits(resp.json())


async def bm25_search(
    q: str,
    *,
    k: int = 10,
    optimize: bool = False,
    category: str | None = None,
    published_from: date | None = None,
    published_to: date | None = None,
    _optimized: OptimizedQuery | None = None,
) -> list[SearchHit]:
    """BM25 lexical search. With optimize=True, expands the query with
    synonyms/acronyms/technical terms before matching — see query_optimizer.py."""
    if _optimized is None and optimize:
        _optimized = await _try_optimize(q)

    query_text = _optimized.bm25_query if _optimized is not None else q
    body = build_bm25_query(
        query_text,
        k=k,
        category=category,
        published_from=published_from,
        published_to=published_to,
    )
    resp = await get_os_client().post(f"/{INDEX_NAME}/_search", json=body)
    resp.raise_for_status()
    return parse_hits(resp.json())


async def hybrid_search(
    q: str,
    *,
    k: int = 10,
    candidates: int = 50,
    rerank: bool = True,
    optimize: bool = False,
    category: str | None = None,
    published_from: date | None = None,
    published_to: date | None = None,
) -> list[SearchHit]:
    """BM25 + dense retrieval fused with RRF, optionally cross-encoder reranked.

    The rerank toggle is a first-class pipeline stage so the Phase 6 eval can
    A/B hybrid vs hybrid+reranker on identical candidate sets. Scores are RRF
    scores when rerank=False and cross-encoder relevance scores when True —
    either way only comparable within a single query's result list.

    With optimize=True, one LLM call produces a BM25-tailored keyword rewrite
    and a HyDE passage for dense — computed once here and shared by both legs
    so they optimize against a consistent understanding of the query, and so
    a single extra round trip (not two) is paid. Reranking always reads the
    original `q`: the cross-encoder needs no rewriting, and the ranking must
    reflect what the user actually asked.
    """
    optimized = await _try_optimize(q) if optimize else None

    bm25_hits, dense_hits = await asyncio.gather(
        bm25_search(
            q,
            k=candidates,
            category=category,
            published_from=published_from,
            published_to=published_to,
            _optimized=optimized,
        ),
        dense_search(
            q,
            k=candidates,
            category=category,
            published_from=published_from,
            published_to=published_to,
            _optimized=optimized,
        ),
    )
    hits_by_id: dict[str, SearchHit] = {}
    for hit in [*bm25_hits, *dense_hits]:
        hits_by_id.setdefault(hit.arxiv_id, hit)

    fused = reciprocal_rank_fusion(
        [
            [hit.arxiv_id for hit in bm25_hits],
            [hit.arxiv_id for hit in dense_hits],
        ]
    )
    if not rerank:
        return [
            hits_by_id[doc_id].model_copy(update={"score": score}) for doc_id, score in fused[:k]
        ]

    pool = [
        (doc_id, paper_chunk(hits_by_id[doc_id].title, hits_by_id[doc_id].abstract))
        for doc_id, _ in fused[:candidates]
    ]
    reranked = await asyncio.to_thread(get_reranker().rerank, q, pool, top_k=k)
    return [hits_by_id[doc_id].model_copy(update={"score": score}) for doc_id, score in reranked]
