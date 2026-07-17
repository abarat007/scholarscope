from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_session
from src.models.paper import Paper
from src.schemas.extraction import PaperExtraction
from src.schemas.landscape import PaperCard
from src.services.cache.cache import get_cache
from src.services.extraction.extractor import cache_key

router = APIRouter(prefix="/papers")


@router.get("/{arxiv_id:path}", response_model=PaperCard)
async def get_paper_card(
    arxiv_id: str, session: Annotated[AsyncSession, Depends(get_session)]
) -> PaperCard:
    """Paper title + cached extraction, for the reading map's detail card."""
    row = (
        await session.execute(select(Paper).where(Paper.arxiv_id == arxiv_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=f"unknown paper {arxiv_id!r}")

    cached = await get_cache().get(cache_key(arxiv_id))
    extraction = PaperExtraction.model_validate_json(cached) if cached else None
    return PaperCard(arxiv_id=arxiv_id, title=row.title, extraction=extraction)
