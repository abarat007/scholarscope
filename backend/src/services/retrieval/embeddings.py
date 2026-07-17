"""Sentence-transformer embeddings (bge-small-en-v1.5, 384 dims).

The model import/load is lazy so that the API process starts fast and unit
tests can inject a fake model. bge models expect a retrieval instruction
prefix on *queries* but not on passages; embeddings are L2-normalized so
cosine similarity matches the index's space_type.
"""

from src.config import get_settings

QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class EmbeddingService:
    def __init__(self, model_name: str | None = None, model=None):
        self._model_name = model_name or get_settings().embedding_model
        self._model = model  # injectable for tests

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # heavy; keep lazy

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._load().encode(
            texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False
        )
        return [list(map(float, v)) for v in vectors]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_passages([QUERY_PREFIX + text])[0]


_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    global _service
    if _service is None:
        _service = EmbeddingService()
    return _service
