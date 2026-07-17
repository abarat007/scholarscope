from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_session
from src.models.paper import Paper
from src.schemas.landscape import BuildResult, LandscapeGraph
from src.services.synthesis.graph import build_graph
from src.services.synthesis.pipeline import build_or_update_topic
from src.services.synthesis.repository import load_landscape

router = APIRouter(prefix="/landscape")

Session = Annotated[AsyncSession, Depends(get_session)]


@router.post("/{topic}/build", response_model=BuildResult)
async def build_topic(
    topic: str,
    session: Session,
    papers: Annotated[int, Query(ge=5, le=50)] = 30,
) -> BuildResult:
    """Build a topic's landscape, or grow an existing one with new papers."""
    try:
        return await build_or_update_topic(session, topic, paper_count=papers)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{topic}", response_model=LandscapeGraph)
async def get_landscape(topic: str, session: Session) -> LandscapeGraph:
    payload = await load_landscape(session, topic)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"no landscape for topic {topic!r}")

    paper_ids = list(payload.paper_versions)
    rows = await session.execute(
        select(Paper.arxiv_id, Paper.title).where(Paper.arxiv_id.in_(paper_ids))
    )
    titles = dict(rows.all())
    return build_graph(payload, titles)
