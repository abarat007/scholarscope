"""Per-retriever query optimization: BM25 keyword expansion + HyDE for dense.

One structured LLM call before retrieval, tailored to what each retriever
actually rewards:

- BM25 is lexical — it wants more/better *keywords*: synonyms, expanded
  acronyms, and additional discriminating technical terms. It cannot benefit
  from a rewrite that changes vocabulary without adding matchable terms.
- Dense vector search embeds the query and compares it to document embeddings
  in the same space. A bare question is a worse proxy for "what a relevant
  document looks like" than a short hypothetical answer passage is — this is
  HyDE (Gao et al., 2022, "Precise Zero-Shot Dense Retrieval without Relevance
  Labels"). The hypothetical passage is embedded with embed_passages (no query
  instruction prefix), matching how real documents were indexed.

The original query is always used for reranking (the cross-encoder reads full
text and needs no rewriting) and for topic/cache identity (which must track
the user's actual words, not an LLM's rewrite of them).

This is a precision/recall aid, not a fix for missing corpus coverage — it
cannot surface documents that were never ingested.
"""

from src.schemas.query_optimization import OptimizedQuery
from src.services.llm.client import LLMUsage, StructuredLLM

OPTIMIZER_SYSTEM_PROMPT = (
    "You prepare a research query for two different retrieval systems. Given a "
    "user's research topic or question, produce (1) a keyword-expanded version "
    "for BM25 lexical search, and (2) a short hypothetical abstract for dense "
    "vector search (the HyDE technique). Stay strictly on the topic given — "
    "never introduce a different subject or narrow/broaden it."
)


async def optimize_query(
    query: str, llm: StructuredLLM, usage: LLMUsage | None = None
) -> OptimizedQuery:
    result = await llm.parse(
        system=OPTIMIZER_SYSTEM_PROMPT,
        user=f"Query: {query}",
        schema=OptimizedQuery,
        max_tokens=600,
    )
    if usage is not None:
        usage.add(result.usage)
    optimized = result.output
    assert isinstance(optimized, OptimizedQuery)
    return optimized
