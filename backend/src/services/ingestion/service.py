import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.ingest import IngestResult
from src.services.ingestion.arxiv_client import ArxivClient
from src.services.ingestion.chunking import paper_chunk
from src.services.ingestion.repository import upsert_papers
from src.services.retrieval.embeddings import get_embedding_service
from src.services.retrieval.indexing import bulk_index_papers
from src.services.retrieval.os_client import get_os_client


async def ingest_category(
    session: AsyncSession,
    client: ArxivClient,
    *,
    category: str,
    days_back: int = 2,
    max_results: int = 200,
) -> IngestResult:
    """Pull the latest papers for one arXiv category, upsert, and index them.

    Fetches newest-first, then keeps papers published or revised within the
    window — the daily DAG uses a 2-day window so a missed run self-heals.
    """
    papers = await client.search(f"cat:{category}", max_results=max_results)
    cutoff = datetime.now(UTC) - timedelta(days=days_back)
    recent = [p for p in papers if p.published_at >= cutoff or p.updated_at >= cutoff]
    inserted, updated = await upsert_papers(session, recent)

    indexed = 0
    if recent:
        texts = [paper_chunk(p.title, p.abstract) for p in recent]
        vectors = await asyncio.to_thread(get_embedding_service().embed_passages, texts)
        indexed = await bulk_index_papers(get_os_client(), recent, vectors)

    return IngestResult(
        category=category,
        fetched=len(papers),
        within_window=len(recent),
        inserted=inserted,
        updated=updated,
        indexed=indexed,
    )
