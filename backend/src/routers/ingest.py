from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_session
from src.schemas.ingest import IngestRequest, IngestResult
from src.services.ingestion.arxiv_client import ArxivClient
from src.services.ingestion.service import ingest_category

router = APIRouter(prefix="/ingest")


@router.post("/arxiv", response_model=IngestResult)
async def ingest_arxiv(
    request: IngestRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> IngestResult:
    """Fetch recent papers for a category and upsert them. Called by the Airflow DAG."""
    client = ArxivClient()
    try:
        return await ingest_category(
            session,
            client,
            category=request.category,
            days_back=request.days_back,
            max_results=request.max_results,
        )
    finally:
        await client.aclose()
