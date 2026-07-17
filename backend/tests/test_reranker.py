from src.services.retrieval.reranker import Reranker


class FakeCrossEncoder:
    """Scores by how many query words appear in the candidate text."""

    def __init__(self):
        self.pairs: list[tuple[str, str]] = []

    def predict(self, pairs):
        self.pairs = list(pairs)
        return [
            sum(word in text.lower() for word in query.lower().split())
            for query, text in pairs
        ]


def test_rerank_orders_by_cross_encoder_score():
    reranker = Reranker(model_name="fake", model=FakeCrossEncoder())
    candidates = [
        ("weak", "unrelated content"),
        ("strong", "retrieval augmented generation survey"),
        ("medium", "a retrieval system"),
    ]

    ranked = reranker.rerank("retrieval augmented generation", candidates, top_k=3)

    assert [doc_id for doc_id, _ in ranked] == ["strong", "medium", "weak"]


def test_rerank_truncates_to_top_k():
    reranker = Reranker(model_name="fake", model=FakeCrossEncoder())
    candidates = [(f"doc{i}", f"text {i}") for i in range(10)]

    ranked = reranker.rerank("text", candidates, top_k=3)

    assert len(ranked) == 3


def test_rerank_pairs_query_with_each_candidate():
    fake = FakeCrossEncoder()
    reranker = Reranker(model_name="fake", model=fake)

    reranker.rerank("the query", [("a", "text a"), ("b", "text b")], top_k=2)

    assert fake.pairs == [("the query", "text a"), ("the query", "text b")]


def test_rerank_empty_candidates_returns_empty():
    reranker = Reranker(model_name="fake", model=FakeCrossEncoder())
    assert reranker.rerank("q", [], top_k=5) == []
