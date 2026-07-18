"""Semantic query cache over Redis.

Two layers, both with hit-rate counters:

1. Topic canonicalization (permanent): a query whose embedding is within
   SIMILARITY_THRESHOLD of an existing topic's embedding maps to that topic,
   so "rag systems" and "retrieval augmented generation" grow one landscape
   instead of two. Stored vectors live in a redis hash; the linear scan is
   fine at reading-map scale (hundreds of topics).

2. Response cache (TTL): recent build results per canonical topic, so
   repeated builds within the window return instantly. New corpus papers
   arrive at most daily, so a short TTL bounds staleness.
"""

import asyncio
import json
import logging

from src.schemas.landscape import BuildResult
from src.services.cache.cache import KVCache, get_cache
from src.services.retrieval.embeddings import EmbeddingService
from src.services.synthesis.clustering import cosine_similarity

log = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.95
RESPONSE_TTL_S = 3600

TOPIC_VECTORS_KEY = "semantic:topic_vectors"  # topic -> json vector
HITS_KEY = "semantic:hits"
MISSES_KEY = "semantic:misses"


class SemanticTopicCache:
    def __init__(self, kv: KVCache | None = None, *, threshold: float = SIMILARITY_THRESHOLD):
        self._kv = kv or get_cache()
        self._threshold = threshold

    async def _load_topic_vectors(self) -> dict[str, list[float]]:
        raw = await self._kv.get(TOPIC_VECTORS_KEY)
        return json.loads(raw) if raw else {}

    async def _bump(self, key: str) -> int:
        raw = await self._kv.get(key)
        count = (int(raw) if raw else 0) + 1
        await self._kv.set(key, str(count))
        return count

    async def _log_rate(self) -> None:
        hits = int(await self._kv.get(HITS_KEY) or 0)
        misses = int(await self._kv.get(MISSES_KEY) or 0)
        total = hits + misses
        if total:
            log.info("semantic cache hit rate: %.0f%% (%d/%d)", 100 * hits / total, hits, total)

    async def canonical_topic(self, query: str, embedder: EmbeddingService) -> tuple[str, bool]:
        """Map a query to an existing topic when semantically equivalent.

        Returns (topic, was_hit). On miss the query becomes a new topic and
        its vector is registered.
        """
        normalized = " ".join(query.lower().split())
        vectors = await self._load_topic_vectors()

        if normalized in vectors:
            await self._bump(HITS_KEY)
            await self._log_rate()
            return normalized, True

        vector = (await asyncio.to_thread(embedder.embed_passages, [normalized]))[0]
        best_topic, best_score = None, 0.0
        for topic, stored in vectors.items():
            score = cosine_similarity(vector, stored)
            if score > best_score:
                best_topic, best_score = topic, score

        if best_topic is not None and best_score >= self._threshold:
            await self._bump(HITS_KEY)
            await self._log_rate()
            log.info("semantic match: %r -> %r (%.3f)", normalized, best_topic, best_score)
            return best_topic, True

        vectors[normalized] = vector
        await self._kv.set(TOPIC_VECTORS_KEY, json.dumps(vectors))
        await self._bump(MISSES_KEY)
        await self._log_rate()
        return normalized, False

    async def get_response(self, topic: str) -> BuildResult | None:
        raw = await self._kv.get(f"landscape:response:{topic}")
        if raw is None:
            return None
        data = json.loads(raw)
        return BuildResult.model_validate(data)

    async def set_response(self, topic: str, result: BuildResult) -> None:
        await self._kv.set(
            f"landscape:response:{topic}", result.model_dump_json(), ttl_s=RESPONSE_TTL_S
        )


_semantic_cache: SemanticTopicCache | None = None


def get_semantic_cache() -> SemanticTopicCache:
    global _semantic_cache
    if _semantic_cache is None:
        _semantic_cache = SemanticTopicCache()
    return _semantic_cache
