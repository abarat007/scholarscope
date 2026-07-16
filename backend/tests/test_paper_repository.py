"""Integration tests for paper upserts against the dockerized Postgres.

Run with `make test-integration` (requires `make start` first). The suite
connects to the host-published port and cleans up its own fixtures.
"""

import os
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from src.config import Settings
from src.models import Base, Paper
from src.schemas.paper import ArxivPaper
from src.services.ingestion.repository import upsert_papers

pytestmark = pytest.mark.integration

TEST_PREFIX = "test-upsert-"


def _paper(suffix: str, *, title: str = "Original title", version: int = 1) -> ArxivPaper:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    return ArxivPaper(
        arxiv_id=f"{TEST_PREFIX}{suffix}",
        version=version,
        title=title,
        abstract="An abstract.",
        authors=["A. Author"],
        categories=["cs.CL"],
        primary_category="cs.CL",
        published_at=now,
        updated_at=now,
        pdf_url=f"https://arxiv.org/pdf/{suffix}",
    )


@pytest.fixture
async def session():
    # Default to the compose host mapping (5433) — never fall back to 5432,
    # which may belong to an unrelated local Postgres.
    settings = Settings(
        _env_file=None,
        postgres_port=int(os.environ.get("POSTGRES_PORT", "5433")),
    )
    engine = create_async_engine(settings.postgres_async_dsn)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        await s.execute(delete(Paper).where(Paper.arxiv_id.startswith(TEST_PREFIX)))
        await s.commit()
        yield s
        await s.execute(delete(Paper).where(Paper.arxiv_id.startswith(TEST_PREFIX)))
        await s.commit()
    await engine.dispose()


async def test_upsert_inserts_then_updates_idempotently(session):
    first = [_paper("0001"), _paper("0002")]
    inserted, updated = await upsert_papers(session, first)
    assert (inserted, updated) == (2, 0)

    # Re-ingesting the same papers with a revision must update, not duplicate.
    revised = [_paper("0001", title="Revised title", version=2), _paper("0002")]
    inserted, updated = await upsert_papers(session, revised)
    assert (inserted, updated) == (0, 2)

    rows = (
        (
            await session.execute(
                select(Paper).where(Paper.arxiv_id.startswith(TEST_PREFIX)).order_by(Paper.arxiv_id)
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 2
    assert rows[0].title == "Revised title"
    assert rows[0].version == 2
    assert rows[0].last_seen_at >= rows[0].first_ingested_at


async def test_upsert_dedupes_within_batch(session):
    dupes = [_paper("0003", title="first"), _paper("0003", title="last wins")]
    inserted, updated = await upsert_papers(session, dupes)
    assert (inserted, updated) == (1, 0)

    row = (
        await session.execute(select(Paper).where(Paper.arxiv_id == f"{TEST_PREFIX}0003"))
    ).scalar_one()
    assert row.title == "last wins"
