"""Cross-encoder reranking of fused candidates.

A cross-encoder scores (query, passage) pairs jointly, which is far more
accurate than bi-encoder similarity but too slow to run over the whole corpus
— so it only reranks the top fused candidates. Lazy-loaded and injectable,
same pattern as the embedding service.
"""

from src.config import get_settings


class Reranker:
    def __init__(self, model_name: str | None = None, model=None):
        self._model_name = model_name or get_settings().reranker_model
        self._model = model  # injectable for tests

    def _load(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder  # heavy; keep lazy

            self._model = CrossEncoder(self._model_name)
        return self._model

    def rerank(
        self, query: str, candidates: list[tuple[str, str]], *, top_k: int
    ) -> list[tuple[str, float]]:
        """Score (id, text) candidates against the query; best-first top_k."""
        if not candidates:
            return []
        scores = self._load().predict([(query, text) for _, text in candidates])
        ranked = sorted(
            zip((doc_id for doc_id, _ in candidates), map(float, scores), strict=True),
            key=lambda item: (-item[1], item[0]),
        )
        return ranked[:top_k]


_reranker: Reranker | None = None


def get_reranker() -> Reranker:
    global _reranker
    if _reranker is None:
        _reranker = Reranker()
    return _reranker
