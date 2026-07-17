"""Retrieval over the papers index.

Query builders are pure functions returning OpenSearch request bodies, so the
exact BM25/k-NN DSL is unit-testable and visible in one place.
"""

import asyncio
from datetime import date

from src.schemas.search import SearchHit
from src.services.retrieval.embeddings import get_embedding_service
from src.services.retrieval.indexing import INDEX_NAME
from src.services.retrieval.os_client import get_os_client

SOURCE_FIELDS = ["arxiv_id", "title", "abstract", "primary_category", "published_at"]


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
    category: str | None = None,
    published_from: date | None = None,
    published_to: date | None = None,
) -> list[SearchHit]:
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
    category: str | None = None,
    published_from: date | None = None,
    published_to: date | None = None,
) -> list[SearchHit]:
    body = build_bm25_query(
        q, k=k, category=category, published_from=published_from, published_to=published_to
    )
    resp = await get_os_client().post(f"/{INDEX_NAME}/_search", json=body)
    resp.raise_for_status()
    return parse_hits(resp.json())
