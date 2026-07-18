from src.schemas.landscape import BuildResult
from src.services.cache.cache import InMemoryCache
from src.services.cache.semantic import RESPONSE_TTL_S, SemanticTopicCache


class OneVectorPerTextEmbedder:
    """Deterministic embeddings: near-identical for configured synonym pairs."""

    VECTORS = {
        "retrieval augmented generation": [1.0, 0.0, 0.0],
        "rag systems overview": [0.99, 0.14, 0.0],  # cosine ~0.99 with the above
        "graph neural networks": [0.0, 1.0, 0.0],
    }

    def embed_passages(self, texts):
        return [self.VECTORS[t] for t in texts]


def _result(topic: str) -> BuildResult:
    return BuildResult(
        topic=topic,
        version=1,
        papers=10,
        new_papers=10,
        clusters=3,
        rebuilt=False,
        input_tokens=100,
        output_tokens=20,
        cost_usd=0.001,
    )


async def test_first_query_registers_new_topic():
    cache = SemanticTopicCache(InMemoryCache())
    topic, hit = await cache.canonical_topic(
        "Retrieval  Augmented   Generation", OneVectorPerTextEmbedder()
    )
    assert topic == "retrieval augmented generation"  # normalized
    assert hit is False


async def test_semantically_equivalent_query_maps_to_existing_topic():
    cache = SemanticTopicCache(InMemoryCache())
    embedder = OneVectorPerTextEmbedder()

    await cache.canonical_topic("retrieval augmented generation", embedder)
    topic, hit = await cache.canonical_topic("rag systems overview", embedder)

    assert topic == "retrieval augmented generation"
    assert hit is True


async def test_distinct_topic_is_not_conflated():
    cache = SemanticTopicCache(InMemoryCache())
    embedder = OneVectorPerTextEmbedder()

    await cache.canonical_topic("retrieval augmented generation", embedder)
    topic, hit = await cache.canonical_topic("graph neural networks", embedder)

    assert topic == "graph neural networks"
    assert hit is False


async def test_exact_repeat_is_a_hit_without_embedding():
    kv = InMemoryCache()
    cache = SemanticTopicCache(kv)
    embedder = OneVectorPerTextEmbedder()

    await cache.canonical_topic("graph neural networks", embedder)
    topic, hit = await cache.canonical_topic("graph  neural  networks", embedder)

    assert (topic, hit) == ("graph neural networks", True)
    assert kv.data["semantic:hits"] == "1"
    assert kv.data["semantic:misses"] == "1"


async def test_response_cache_round_trips_with_ttl():
    kv = InMemoryCache()
    cache = SemanticTopicCache(kv)

    assert await cache.get_response("rag") is None
    await cache.set_response("rag", _result("rag"))
    cached = await cache.get_response("rag")

    assert cached is not None and cached.topic == "rag"
    assert kv.ttls["landscape:response:rag"] == RESPONSE_TTL_S
