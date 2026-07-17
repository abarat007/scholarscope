import time
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from src.schemas.search import SearchResponse
from src.services.retrieval import search as search_service

router = APIRouter(prefix="/search")

QueryText = Annotated[str, Query(min_length=1, max_length=500)]
TopK = Annotated[int, Query(ge=1, le=50)]


@router.get("/bm25", response_model=SearchResponse)
async def search_bm25(
    q: QueryText,
    k: TopK = 10,
    category: str | None = None,
    published_from: date | None = None,
    published_to: date | None = None,
) -> SearchResponse:
    started = time.perf_counter()
    hits = await search_service.bm25_search(
        q, k=k, category=category, published_from=published_from, published_to=published_to
    )
    return SearchResponse(
        query=q,
        mode="bm25",
        took_ms=round((time.perf_counter() - started) * 1000, 1),
        hits=hits,
    )
