"""Topic pipeline: retrieve -> extract -> synthesize/merge -> persist."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.models.paper import Paper
from src.schemas.landscape import BuildResult
from src.schemas.paper import ArxivPaper
from src.services.extraction.extractor import extract_many
from src.services.llm.client import get_llm
from src.services.retrieval.embeddings import get_embedding_service
from src.services.retrieval.search import hybrid_search
from src.services.synthesis.repository import load_landscape, normalize_topic, save_landscape
from src.services.synthesis.synthesizer import build_landscape

log = logging.getLogger(__name__)


def _row_to_schema(row: Paper) -> ArxivPaper:
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


async def build_or_update_topic(
    session: AsyncSession, topic: str, *, paper_count: int = 30
) -> BuildResult:
    topic = normalize_topic(topic)

    hits = await hybrid_search(topic, k=paper_count, candidates=max(60, paper_count), rerank=True)
    if not hits:
        raise ValueError(f"no papers retrieved for topic {topic!r}")

    ids = [hit.arxiv_id for hit in hits]
    rows = (
        (await session.execute(select(Paper).where(Paper.arxiv_id.in_(ids)))).scalars().all()
    )
    papers = [_row_to_schema(r) for r in rows]

    extractions, usage = await extract_many(papers)

    existing = await load_landscape(session, topic)
    if existing is None:
        payload = await build_landscape(
            topic,
            papers,
            extractions,
            embedder=get_embedding_service(),
            llm=get_llm(),
            usage=usage,
        )
        new_papers, rebuilt = len(papers), False
    else:
        from src.services.synthesis.merge import merge_landscape

        payload, new_papers, rebuilt = await merge_landscape(
            existing,
            papers,
            extractions,
            embedder=get_embedding_service(),
            llm=get_llm(),
            usage=usage,
        )

    await save_landscape(session, payload)
    settings = get_settings()
    result = BuildResult(
        topic=topic,
        version=payload.version,
        papers=len(payload.paper_versions),
        new_papers=new_papers,
        clusters=len(payload.clusters),
        rebuilt=rebuilt,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cost_usd=usage.cost_usd(
            settings.llm_input_cost_per_mtok, settings.llm_output_cost_per_mtok
        ),
    )
    log.info("landscape build %s", result.model_dump())
    return result
