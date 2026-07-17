from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SearchHit(BaseModel):
    arxiv_id: str
    title: str
    abstract: str
    primary_category: str
    published_at: datetime
    score: float


class SearchResponse(BaseModel):
    query: str
    mode: Literal["bm25", "dense", "hybrid"]
    reranked: bool | None = None  # only meaningful for hybrid
    took_ms: float
    hits: list[SearchHit]
