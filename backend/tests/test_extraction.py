from datetime import UTC, datetime

from src.schemas.extraction import EXTRACTION_SCHEMA_VERSION, PaperExtraction
from src.schemas.paper import ArxivPaper
from src.services.cache.cache import InMemoryCache
from src.services.extraction.extractor import cache_key, extract_many, extract_paper
from src.services.llm.client import LLMResult, LLMUsage

SAMPLE_EXTRACTION = PaperExtraction(
    problem="Retrieval quality degrades on long-tail queries.",
    method="A hybrid retriever with reranking.",
    results="Precision@5 improves by 18%.",
    contribution="A cheap reranking stage.",
    limitations="Abstract-only evaluation.",
    key_terms=["retrieval", "reranking"],
)


class FakeLLM:
    def __init__(self):
        self.calls = 0

    async def parse(self, *, system, user, schema, max_tokens=2000):
        self.calls += 1
        assert schema is PaperExtraction
        return LLMResult(output=SAMPLE_EXTRACTION, usage=LLMUsage(1000, 200))


def _paper(suffix: str) -> ArxivPaper:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    return ArxivPaper(
        arxiv_id=f"2601.{suffix}",
        version=1,
        title=f"Paper {suffix}",
        abstract="An abstract about retrieval.",
        authors=["A"],
        categories=["cs.CL"],
        primary_category="cs.CL",
        published_at=now,
        updated_at=now,
        pdf_url="https://example.org",
    )


def test_cache_key_includes_schema_version():
    assert cache_key("2601.00001") == f"extraction:v{EXTRACTION_SCHEMA_VERSION}:2601.00001"


async def test_extract_paper_caches_and_skips_llm_on_second_call():
    llm, cache = FakeLLM(), InMemoryCache()
    paper = _paper("00001")

    first = await extract_paper(paper, llm=llm, cache=cache)
    second = await extract_paper(paper, llm=llm, cache=cache)

    assert llm.calls == 1  # second call served from cache
    assert first == second == SAMPLE_EXTRACTION
    assert cache_key(paper.arxiv_id) in cache.data


async def test_extract_paper_accumulates_usage_only_on_llm_calls():
    llm, cache = FakeLLM(), InMemoryCache()
    usage = LLMUsage()

    await extract_paper(_paper("00002"), llm=llm, cache=cache, usage=usage)
    await extract_paper(_paper("00002"), llm=llm, cache=cache, usage=usage)

    assert (usage.input_tokens, usage.output_tokens) == (1000, 200)


async def test_extract_many_bounds_concurrency_and_totals_usage():
    llm, cache = FakeLLM(), InMemoryCache()
    papers = [_paper(f"{i:05d}") for i in range(7)]

    extractions, usage = await extract_many(papers, llm=llm, cache=cache, concurrency=3)

    assert len(extractions) == 7
    assert llm.calls == 7
    assert usage.input_tokens == 7000
    assert usage.cost_usd(2.0, 10.0) == round(7000 / 1e6 * 2.0 + 1400 / 1e6 * 10.0, 6)
