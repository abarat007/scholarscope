from pydantic import BaseModel, Field


class OptimizedQuery(BaseModel):
    """Per-retriever query rewrites produced by one structured LLM call.

    BM25 and dense vector search reward different things — see
    services/retrieval/query_optimizer.py for the reasoning.
    """

    bm25_query: str = Field(
        description=(
            "Keyword-optimized rewrite of the query for BM25 lexical search: the "
            "original terms plus synonyms, expanded abbreviations/acronyms, and "
            "additional discriminating technical terms a relevant paper would use. "
            "Do not introduce a different topic."
        )
    )
    hyde_passage: str = Field(
        description=(
            "A short hypothetical paper abstract (2-4 sentences) that would "
            "plausibly answer or address the query, written in the register of a "
            "real academic abstract. Used only to seed dense vector search via the "
            "HyDE technique — never shown to the user, and must not claim to be a "
            "real paper or cite real results."
        )
    )
