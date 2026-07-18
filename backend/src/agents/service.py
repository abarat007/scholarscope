"""Production wiring for the landscape agent graph."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.graph import AgentDeps
from src.agents.state import AgentState
from src.config import get_settings
from src.models.paper import Paper
from src.schemas.landscape import BuildResult, LandscapePayload
from src.schemas.search import SearchHit
from src.services.cache.semantic import get_semantic_cache
from src.services.extraction.extractor import extract_many
from src.services.guardrails.output_rails import check_output
from src.services.llm.client import LLMUsage, get_llm
from src.services.retrieval.embeddings import get_embedding_service
from src.services.retrieval.search import hybrid_search
from src.services.synthesis.merge import merge_landscape
from src.services.synthesis.pipeline import row_to_schema
from src.services.synthesis.repository import load_landscape, save_landscape
from src.services.synthesis.synthesizer import build_landscape

log = logging.getLogger(__name__)


def make_agent_deps(session: AsyncSession) -> AgentDeps:
    usage = LLMUsage()
    llm = get_llm()
    embedder = get_embedding_service()
    semantic_cache = get_semantic_cache()

    async def synthesize_fn(
        topic: str, hits: list[SearchHit]
    ) -> tuple[LandscapePayload, set[str], int, bool]:
        ids = [hit.arxiv_id for hit in hits]
        rows = (
            (await session.execute(select(Paper).where(Paper.arxiv_id.in_(ids))))
            .scalars()
            .all()
        )
        papers = [row_to_schema(r) for r in rows]
        if not papers:
            raise ValueError(f"no papers found for topic {topic!r}")
        extractions, _ = await extract_many(papers, llm=llm)
        existing = await load_landscape(session, topic)
        allowed_ids = {p.arxiv_id for p in papers}
        if existing is None:
            payload = await build_landscape(
                topic, papers, extractions, embedder=embedder, llm=llm, usage=usage
            )
            return payload, allowed_ids, len(papers), False
        allowed_ids |= set(existing.paper_versions)
        payload, new_papers, rebuilt = await merge_landscape(
            existing, papers, extractions, embedder=embedder, llm=llm, usage=usage
        )
        return payload, allowed_ids, new_papers, rebuilt

    async def finalize_fn(state: AgentState) -> BuildResult | dict:
        payload: LandscapePayload = state["payload"]
        cited = {pid for c in payload.clusters for pid in c.paper_ids}
        known = set(
            (
                await session.execute(select(Paper.arxiv_id).where(Paper.arxiv_id.in_(cited)))
            ).scalars()
        )
        outcome = check_output(payload, allowed_ids=state["allowed_ids"], known_ids=known)
        if outcome.rejected:
            log.error("output rails rejected landscape for %r: %s", payload.topic, outcome.reason)
            return {
                "rail": "output_check",
                "reason": outcome.reason or "citation verification failed",
                "message": "The synthesized landscape failed citation verification.",
            }
        if outcome.removed_paper_ids:
            log.warning(
                "output rails stripped %d unverified papers from %r",
                len(outcome.removed_paper_ids),
                payload.topic,
            )
        await save_landscape(session, outcome.payload)

        settings = get_settings()
        result = BuildResult(
            topic=outcome.payload.topic,
            version=outcome.payload.version,
            papers=len(outcome.payload.paper_versions),
            new_papers=state["new_papers"],
            clusters=len(outcome.payload.clusters),
            rebuilt=state["rebuilt"],
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cost_usd=usage.cost_usd(
                settings.llm_input_cost_per_mtok, settings.llm_output_cost_per_mtok
            ),
        )
        await semantic_cache.set_response(outcome.payload.topic, result)
        log.info("landscape build %s", result.model_dump())
        return result

    return AgentDeps(
        llm=llm,
        embedder=embedder,
        semantic_cache=semantic_cache,
        usage=usage,
        search_fn=hybrid_search,
        synthesize_fn=synthesize_fn,
        finalize_fn=finalize_fn,
    )
