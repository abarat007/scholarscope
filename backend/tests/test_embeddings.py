from src.services.retrieval.embeddings import QUERY_PREFIX, EmbeddingService


class FakeModel:
    def __init__(self):
        self.calls: list[list[str]] = []

    def encode(self, texts, **kwargs):
        self.calls.append(list(texts))
        return [[float(len(t)), 0.5] for t in texts]


def test_embed_passages_returns_float_lists():
    fake = FakeModel()
    service = EmbeddingService(model_name="fake", model=fake)

    vectors = service.embed_passages(["abc", "defgh"])

    assert vectors == [[3.0, 0.5], [5.0, 0.5]]
    assert fake.calls == [["abc", "defgh"]]


def test_embed_query_applies_bge_retrieval_prefix():
    fake = FakeModel()
    service = EmbeddingService(model_name="fake", model=fake)

    service.embed_query("what is rag?")

    assert fake.calls == [[QUERY_PREFIX + "what is rag?"]]


def test_empty_input_never_touches_the_model():
    fake = FakeModel()
    service = EmbeddingService(model_name="fake", model=fake)

    assert service.embed_passages([]) == []
    assert fake.calls == []
