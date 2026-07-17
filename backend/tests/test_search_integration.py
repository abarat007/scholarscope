"""Integration tests against the dockerized OpenSearch.

Uses a scratch index with handcrafted vectors so no model download is needed;
run via `make test-integration` after `make start`.
"""

import os
import uuid
from datetime import UTC, datetime

import httpx
import pytest
from src.schemas.paper import ArxivPaper
from src.services.retrieval.indexing import bulk_index_papers, ensure_index
from src.services.retrieval.search import build_bm25_query, build_knn_query, parse_hits

pytestmark = pytest.mark.integration

DIMS = 384


def _vector(hot_index: int) -> list[float]:
    v = [0.0] * DIMS
    v[hot_index] = 1.0
    return v


def _paper(suffix: str, title: str, abstract: str, category: str = "cs.CL") -> ArxivPaper:
    now = datetime(2026, 3, 1, tzinfo=UTC)
    return ArxivPaper(
        arxiv_id=f"it-{suffix}",
        version=1,
        title=title,
        abstract=abstract,
        authors=["A. Author"],
        categories=[category],
        primary_category=category,
        published_at=now,
        updated_at=now,
        pdf_url="https://example.org/pdf",
    )


@pytest.fixture
async def scratch_index():
    base_url = os.environ.get("OPENSEARCH_URL", "http://localhost:9200")
    index = f"papers-test-{uuid.uuid4().hex[:8]}"
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        created = await ensure_index(client, index=index)
        assert created
        papers = [
            _paper("rag", "Retrieval augmented generation survey", "All about RAG pipelines."),
            _paper("cv", "Vision transformers at scale", "Image classification models.", "cs.CV"),
            _paper("db", "Query optimization in databases", "Join ordering and planners."),
        ]
        await bulk_index_papers(
            client,
            papers,
            [_vector(0), _vector(100), _vector(200)],
            index=index,
            refresh=True,
        )
        yield client, index
        await client.delete(f"/{index}")


async def test_bm25_round_trip_matches_title_terms(scratch_index):
    client, index = scratch_index
    body = build_bm25_query("retrieval augmented generation", k=3)

    resp = await client.post(f"/{index}/_search", json=body)
    hits = parse_hits(resp.json())

    assert hits and hits[0].arxiv_id == "it-rag"


async def test_bm25_category_filter_excludes_other_categories(scratch_index):
    client, index = scratch_index
    body = build_bm25_query("transformers models", k=3, category="cs.CV")

    resp = await client.post(f"/{index}/_search", json=body)
    hits = parse_hits(resp.json())

    assert [h.arxiv_id for h in hits] == ["it-cv"]


async def test_knn_round_trip_finds_nearest_vector(scratch_index):
    client, index = scratch_index
    near_db = _vector(200)
    near_db[201] = 0.2  # close to the "db" paper's vector, far from the others

    resp = await client.post(f"/{index}/_search", json=build_knn_query(near_db, k=2))
    hits = parse_hits(resp.json())

    assert hits[0].arxiv_id == "it-db"
