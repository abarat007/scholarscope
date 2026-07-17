from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.graph import build_agent_graph
from src.agents.service import make_agent_deps
from src.config import get_settings
from src.db import get_session
from src.models.paper import Paper
from src.schemas.agent import RefusalResponse
from src.schemas.landscape import BuildResult, LandscapeGraph
from src.services.synthesis.graph import build_graph
from src.services.synthesis.repository import load_landscape, normalize_topic

router = APIRouter(prefix="/landscape")

Session = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    "/{topic}/build",
    response_model=BuildResult,
    responses={400: {"model": RefusalResponse}},
)
async def build_topic(
    topic: str,
    session: Session,
    papers: Annotated[int, Query(ge=5, le=50)] = 30,
):
    """Build or grow a topic landscape via the guarded agent graph."""
    if not get_settings().anthropic_api_key:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY is not configured; set it in .env and restart the stack",
        )
    graph = build_agent_graph(make_agent_deps(session))
    try:
        final = await graph.ainvoke(
            {"query": normalize_topic(topic), "paper_count": papers, "refine_count": 0}
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if final.get("refusal"):
        refusal = RefusalResponse(**final["refusal"])
        return JSONResponse(status_code=400, content=refusal.model_dump())
    return final["result"]


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
