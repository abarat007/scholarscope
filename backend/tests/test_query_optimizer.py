from src.schemas.query_optimization import OptimizedQuery
from src.services.llm.client import LLMResult, LLMUsage
from src.services.retrieval.query_optimizer import optimize_query


class ScriptedLLM:
    def __init__(self, optimized: OptimizedQuery):
        self.optimized = optimized
        self.calls: list[tuple[str, type]] = []

    async def parse(self, *, system, user, schema, max_tokens=2000):
        self.calls.append((user, schema))
        return LLMResult(output=self.optimized, usage=LLMUsage(80, 40))


async def test_optimize_query_returns_bm25_and_hyde_fields():
    expected = OptimizedQuery(
        bm25_query="retrieval augmented generation RAG dense passage retrieval",
        hyde_passage="This paper proposes a retrieval-augmented generation method...",
    )
    llm = ScriptedLLM(expected)

    result = await optimize_query("retrieval augmented generation", llm)

    assert result == expected
    assert llm.calls[0][1] is OptimizedQuery
    assert "retrieval augmented generation" in llm.calls[0][0]


async def test_optimize_query_accumulates_usage_when_tracked():
    llm = ScriptedLLM(OptimizedQuery(bm25_query="x", hyde_passage="y"))
    usage = LLMUsage()

    await optimize_query("q", llm, usage)

    assert (usage.input_tokens, usage.output_tokens) == (80, 40)


async def test_optimize_query_usage_is_optional():
    llm = ScriptedLLM(OptimizedQuery(bm25_query="x", hyde_passage="y"))

    # must not raise when usage=None (the default)
    result = await optimize_query("q", llm)

    assert result.bm25_query == "x"
