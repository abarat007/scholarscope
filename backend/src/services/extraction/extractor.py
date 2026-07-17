"""Per-paper structured extraction with permanent caching.

Extractions are deterministic reads of an immutable paper abstract, so a
cache hit is always valid for a given schema version — cache forever.
"""

import asyncio
import logging

from src.config import get_settings
from src.schemas.extraction import EXTRACTION_SCHEMA_VERSION, PaperExtraction
from src.schemas.paper import ArxivPaper
from src.services.cache.cache import KVCache, get_cache
from src.services.llm.client import LLMUsage, StructuredLLM, get_llm

log = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = (
    "You are an expert research analyst. Extract a faithful structured reading "
    "of the paper from its title and abstract. Do not speculate beyond what the "
    "abstract states; write 'not stated' where information is absent. Keep each "
    "field to one or two sentences."
)


def cache_key(arxiv_id: str) -> str:
    return f"extraction:v{EXTRACTION_SCHEMA_VERSION}:{arxiv_id}"


def extraction_prompt(paper: ArxivPaper) -> str:
    return f"Title: {paper.title}\n\nAbstract: {paper.abstract}"


async def extract_paper(
    paper: ArxivPaper,
    *,
    llm: StructuredLLM | None = None,
    cache: KVCache | None = None,
    usage: LLMUsage | None = None,
) -> PaperExtraction:
    """Return the structured extraction for one paper, cached by schema version."""
    cache = cache or get_cache()
    cached = await cache.get(cache_key(paper.arxiv_id))
    if cached is not None:
        return PaperExtraction.model_validate_json(cached)

    llm = llm or get_llm()
    result = await llm.parse(
        system=EXTRACTION_SYSTEM_PROMPT,
        user=extraction_prompt(paper),
        schema=PaperExtraction,
        max_tokens=1500,
    )
    if usage is not None:
        usage.add(result.usage)
    extraction = result.output
    assert isinstance(extraction, PaperExtraction)
    await cache.set(cache_key(paper.arxiv_id), extraction.model_dump_json())
    return extraction


async def extract_many(
    papers: list[ArxivPaper],
    *,
    llm: StructuredLLM | None = None,
    cache: KVCache | None = None,
    concurrency: int = 5,
) -> tuple[dict[str, PaperExtraction], LLMUsage]:
    """Extract papers concurrently (bounded) and log aggregate token cost."""
    llm = llm or get_llm()
    cache = cache or get_cache()
    usage = LLMUsage()
    semaphore = asyncio.Semaphore(concurrency)

    async def bounded(paper: ArxivPaper) -> tuple[str, PaperExtraction]:
        async with semaphore:
            return paper.arxiv_id, await extract_paper(paper, llm=llm, cache=cache, usage=usage)

    pairs = await asyncio.gather(*(bounded(p) for p in papers))
    settings = get_settings()
    log.info(
        "extracted %d papers: %d input + %d output tokens (~$%.4f)",
        len(pairs),
        usage.input_tokens,
        usage.output_tokens,
        usage.cost_usd(settings.llm_input_cost_per_mtok, settings.llm_output_cost_per_mtok),
    )
    return dict(pairs), usage
