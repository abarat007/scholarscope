from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.paper import Paper
from src.schemas.paper import ArxivPaper


async def upsert_papers(session: AsyncSession, papers: list[ArxivPaper]) -> tuple[int, int]:
    """Idempotently upsert papers keyed on arxiv_id. Returns (inserted, updated)."""
    if not papers:
        return 0, 0

    # Dedupe within the batch — ON CONFLICT cannot touch the same row twice.
    by_id = {p.arxiv_id: p for p in papers}
    ids = set(by_id)

    existing = set(
        (await session.execute(select(Paper.arxiv_id).where(Paper.arxiv_id.in_(ids)))).scalars()
    )

    rows = [
        {
            "arxiv_id": p.arxiv_id,
            "version": p.version,
            "title": p.title,
            "abstract": p.abstract,
            "authors": p.authors,
            "categories": p.categories,
            "primary_category": p.primary_category,
            "published_at": p.published_at,
            "updated_at": p.updated_at,
            "pdf_url": p.pdf_url,
        }
        for p in by_id.values()
    ]
    stmt = pg_insert(Paper).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Paper.arxiv_id],
        set_={
            "version": stmt.excluded.version,
            "title": stmt.excluded.title,
            "abstract": stmt.excluded.abstract,
            "authors": stmt.excluded.authors,
            "categories": stmt.excluded.categories,
            "primary_category": stmt.excluded.primary_category,
            "published_at": stmt.excluded.published_at,
            "updated_at": stmt.excluded.updated_at,
            "pdf_url": stmt.excluded.pdf_url,
            "last_seen_at": func.now(),
        },
    )
    await session.execute(stmt)
    await session.commit()

    return len(ids - existing), len(ids & existing)
