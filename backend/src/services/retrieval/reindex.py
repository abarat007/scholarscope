"""Re-embed and re-index the entire Postgres corpus into OpenSearch.

    docker compose exec backend python -m src.services.retrieval.reindex

Safe to re-run: documents are indexed by arxiv_id, so this is an upsert.
"""

import asyncio
import sys

from sqlalchemy import select

from src.db import get_session_factory, init_db
from src.models.paper import Paper
from src.schemas.paper import ArxivPaper
from src.services.ingestion.chunking import paper_chunk
from src.services.retrieval.embeddings import get_embedding_service
from src.services.retrieval.indexing import INDEX_NAME, bulk_index_papers, ensure_index
from src.services.retrieval.os_client import get_os_client

BATCH_SIZE = 128


def _to_schema(row: Paper) -> ArxivPaper:
    return ArxivPaper(
        arxiv_id=row.arxiv_id,
        version=row.version,
        title=row.title,
        abstract=row.abstract,
        authors=row.authors,
        categories=row.categories,
        primary_category=row.primary_category,
        published_at=row.published_at,
        updated_at=row.updated_at,
        pdf_url=row.pdf_url,
    )


async def reindex() -> int:
    await init_db()
    client = get_os_client()
    created = await ensure_index(client)
    print(f"index {INDEX_NAME}: {'created' if created else 'exists'}")

    embedder = get_embedding_service()
    async with get_session_factory()() as session:
        rows = (await session.execute(select(Paper).order_by(Paper.id))).scalars().all()

    total = 0
    for offset in range(0, len(rows), BATCH_SIZE):
        batch = [_to_schema(r) for r in rows[offset : offset + BATCH_SIZE]]
        vectors = embedder.embed_passages([paper_chunk(p.title, p.abstract) for p in batch])
        total += await bulk_index_papers(client, batch, vectors)
        print(f"indexed {total}/{len(rows)}")

    await client.post(f"/{INDEX_NAME}/_refresh")
    return total


if __name__ == "__main__":
    count = asyncio.run(reindex())
    print(f"reindex complete: {count} papers")
    sys.exit(0)
