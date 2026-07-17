from datetime import UTC, datetime

from src.schemas.search import SearchHit
from src.services.retrieval import search as search_module


def _hit(arxiv_id: str, score: float) -> SearchHit:
    return SearchHit(
        arxiv_id=arxiv_id,
        title=f"Paper {arxiv_id}",
        abstract="An abstract.",
        primary_category="cs.CL",
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
        score=score,
    )


def _stub_searches(monkeypatch, bm25_ids: list[str], dense_ids: list[str]):
    async def fake_bm25(q, **kwargs):
        return [_hit(i, 10.0 - n) for n, i in enumerate(bm25_ids)]

    async def fake_dense(q, **kwargs):
        return [_hit(i, 1.0 - n / 10) for n, i in enumerate(dense_ids)]

    monkeypatch.setattr(search_module, "bm25_search", fake_bm25)
    monkeypatch.setattr(search_module, "dense_search", fake_dense)


async def test_hybrid_promotes_docs_found_by_both_retrievers(monkeypatch):
    _stub_searches(monkeypatch, ["a", "b", "c"], ["d", "b", "e"])

    hits = await search_module.hybrid_search("query", k=3)

    assert hits[0].arxiv_id == "b"
    assert len(hits) == 3


async def test_hybrid_scores_are_rrf_not_raw_engine_scores(monkeypatch):
    _stub_searches(monkeypatch, ["a"], ["a"])

    hits = await search_module.hybrid_search("query", k=1)

    # raw scores were 10.0 (bm25) and 1.0 (dense); RRF replaces them
    assert hits[0].score < 1.0


async def test_hybrid_respects_k(monkeypatch):
    _stub_searches(monkeypatch, ["a", "b", "c", "d"], ["e", "f", "g", "h"])

    hits = await search_module.hybrid_search("query", k=5)

    assert len(hits) == 5
