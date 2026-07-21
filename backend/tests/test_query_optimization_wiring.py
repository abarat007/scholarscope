"""Wiring tests: does optimize=True actually change what hits OpenSearch and
the embedder, and does the whole thing degrade gracefully when it can't run?
Unit-level correctness of the optimizer's own output lives in
test_query_optimizer.py — this file is about integration into search.py.
"""

import json

import httpx
from src.schemas.query_optimization import OptimizedQuery
from src.services.retrieval import search as search_module


class FixedEmbedder:
    def __init__(self):
        self.query_calls: list[str] = []
        self.passage_calls: list[list[str]] = []

    def embed_query(self, text):
        self.query_calls.append(text)
        return [1.0, 0.0]

    def embed_passages(self, texts):
        self.passage_calls.append(list(texts))
        return [[0.0, 1.0] for _ in texts]


def _mock_os_client(capture: dict) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        capture["body"] = json.loads(request.content)
        return httpx.Response(200, json={"hits": {"hits": []}})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://os")


async def test_bm25_search_optimize_sends_expanded_query(monkeypatch):
    capture: dict = {}
    monkeypatch.setattr(search_module, "get_os_client", lambda: _mock_os_client(capture))

    async def fake_try_optimize(q):
        return OptimizedQuery(bm25_query="expanded keywords here", hyde_passage="n/a")

    monkeypatch.setattr(search_module, "_try_optimize", fake_try_optimize)

    await search_module.bm25_search("original query", optimize=True)

    sent = capture["body"]["query"]["bool"]["must"][0]["multi_match"]["query"]
    assert sent == "expanded keywords here"


async def test_bm25_search_default_never_calls_optimizer(monkeypatch):
    capture: dict = {}
    monkeypatch.setattr(search_module, "get_os_client", lambda: _mock_os_client(capture))
    calls = {"n": 0}

    async def fake_try_optimize(q):
        calls["n"] += 1
        return OptimizedQuery(bm25_query="x", hyde_passage="y")

    monkeypatch.setattr(search_module, "_try_optimize", fake_try_optimize)

    await search_module.bm25_search("original query")  # optimize defaults to False

    assert calls["n"] == 0
    sent = capture["body"]["query"]["bool"]["must"][0]["multi_match"]["query"]
    assert sent == "original query"


async def test_dense_search_optimize_embeds_hyde_passage_not_the_query(monkeypatch):
    capture: dict = {}
    monkeypatch.setattr(search_module, "get_os_client", lambda: _mock_os_client(capture))
    embedder = FixedEmbedder()
    monkeypatch.setattr(search_module, "get_embedding_service", lambda: embedder)

    async def fake_try_optimize(q):
        return OptimizedQuery(bm25_query="n/a", hyde_passage="a hypothetical abstract")

    monkeypatch.setattr(search_module, "_try_optimize", fake_try_optimize)

    await search_module.dense_search("original query", optimize=True)

    # HyDE passage goes through embed_passages (no query-instruction prefix) —
    # embedding it like a document, not like a question.
    assert embedder.passage_calls == [["a hypothetical abstract"]]
    assert embedder.query_calls == []
    assert capture["body"]["query"]["knn"]["embedding"]["vector"] == [0.0, 1.0]


async def test_dense_search_default_embeds_the_query_normally(monkeypatch):
    capture: dict = {}
    monkeypatch.setattr(search_module, "get_os_client", lambda: _mock_os_client(capture))
    embedder = FixedEmbedder()
    monkeypatch.setattr(search_module, "get_embedding_service", lambda: embedder)

    await search_module.dense_search("original query")

    assert embedder.query_calls == ["original query"]
    assert embedder.passage_calls == []


async def test_hybrid_optimize_calls_optimizer_once_and_shares_result(monkeypatch):
    from tests.test_hybrid_search import _hit  # reuse the existing hit factory

    captured_bm25: dict = {}
    captured_dense: dict = {}

    async def fake_bm25(q, **kwargs):
        captured_bm25["optimized"] = kwargs.get("_optimized")
        return [_hit("a", 1.0)]

    async def fake_dense(q, **kwargs):
        captured_dense["optimized"] = kwargs.get("_optimized")
        return [_hit("a", 1.0)]

    monkeypatch.setattr(search_module, "bm25_search", fake_bm25)
    monkeypatch.setattr(search_module, "dense_search", fake_dense)

    calls = {"n": 0}
    sentinel = OptimizedQuery(bm25_query="x", hyde_passage="y")

    async def fake_try_optimize(q):
        calls["n"] += 1
        return sentinel

    monkeypatch.setattr(search_module, "_try_optimize", fake_try_optimize)

    await search_module.hybrid_search("query", k=1, rerank=False, optimize=True)

    assert calls["n"] == 1  # one shared optimization, not one per retriever leg
    assert captured_bm25["optimized"] is sentinel
    assert captured_dense["optimized"] is sentinel


async def test_hybrid_without_optimize_never_touches_the_optimizer(monkeypatch):
    from tests.test_hybrid_search import _stub_searches

    _stub_searches(monkeypatch, ["a"], ["a"])
    calls = {"n": 0}

    async def fake_try_optimize(q):
        calls["n"] += 1
        return None

    monkeypatch.setattr(search_module, "_try_optimize", fake_try_optimize)

    await search_module.hybrid_search("query", k=1, rerank=False)  # optimize defaults False

    assert calls["n"] == 0


async def test_hybrid_optimize_degrades_gracefully_when_llm_unavailable(monkeypatch):
    """No API key / no credits must never break search — only skip the boost."""
    from tests.test_hybrid_search import _stub_searches

    _stub_searches(monkeypatch, ["a"], ["a"])

    def failing_get_llm():
        raise RuntimeError("no credits")

    monkeypatch.setattr(search_module, "get_llm", failing_get_llm)

    hits = await search_module.hybrid_search("query", k=1, rerank=False, optimize=True)

    assert len(hits) == 1
