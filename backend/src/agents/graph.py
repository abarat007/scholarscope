"""The landscape agent as an explicit LangGraph state machine.

    validate_input -> check_cache -> retrieve -> grade_relevance
        -> (refine_query loop, max MAX_REFINES) -> synthesize
        -> finalize (output rails + persist) -> END

Dependencies are bound at graph-construction time (sessions and clients are
not graph state); every node is a thin closure over `AgentDeps`, so the graph
topology is unit-testable with fully scripted dependencies.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from langgraph.graph import END, StateGraph

from src.agents.state import AgentState
from src.schemas.agent import RefinedQuery, RelevanceGrade
from src.schemas.landscape import BuildResult, LandscapePayload
from src.schemas.search import SearchHit
from src.services.cache.semantic import SemanticTopicCache
from src.services.guardrails.input_rails import REFUSAL_MESSAGE, run_input_rails
from src.services.llm.client import LLMUsage, StructuredLLM
from src.services.observability import get_tracer
from src.services.retrieval.embeddings import EmbeddingService

MAX_REFINES = 2

GRADE_SYSTEM_PROMPT = (
    "You judge whether a retrieved set of papers actually addresses a research "
    "topic. Be strict: titles that merely share buzzwords are not relevant."
)

REFINE_SYSTEM_PROMPT = (
    "The previous search query retrieved poorly matching papers. Rewrite it as "
    "a sharper academic search query for the same underlying topic — expand "
    "abbreviations, add discriminating technical terms, drop filler words."
)

SynthesizeFn = Callable[
    [str, list[SearchHit]], Awaitable[tuple[LandscapePayload, set[str], int, bool]]
]
FinalizeFn = Callable[
    [AgentState], Awaitable[BuildResult | dict]
]  # returns BuildResult or a refusal dict


@dataclass
class AgentDeps:
    llm: StructuredLLM
    embedder: EmbeddingService
    semantic_cache: SemanticTopicCache
    usage: LLMUsage
    search_fn: Callable[..., Awaitable[list[SearchHit]]]
    synthesize_fn: SynthesizeFn
    finalize_fn: FinalizeFn
    check_topicality: bool = True


def _refusal(rail: str, reason: str) -> dict:
    return {"rail": rail, "reason": reason, "message": REFUSAL_MESSAGE}


def build_agent_graph(deps: AgentDeps):
    async def validate_input(state: AgentState) -> dict:
        verdict = await run_input_rails(
            state["query"],
            llm=deps.llm if deps.check_topicality else None,
            usage=deps.usage,
        )
        if not verdict.allowed:
            return {"refusal": _refusal(verdict.rail or "input", verdict.reason or "blocked")}
        return {}

    async def check_cache(state: AgentState) -> dict:
        topic, _ = await deps.semantic_cache.canonical_topic(state["query"], deps.embedder)
        cached = await deps.semantic_cache.get_response(topic)
        if cached is not None:
            return {"topic": topic, "cache_hit": True, "result": cached}
        return {"topic": topic, "cache_hit": False, "current_query": topic}

    async def retrieve(state: AgentState) -> dict:
        hits = await deps.search_fn(
            state["current_query"],
            k=state["paper_count"],
            candidates=max(60, state["paper_count"]),
            rerank=True,
        )
        return {"hits": hits}

    async def grade_relevance(state: AgentState) -> dict:
        if not state["hits"]:
            return {"relevance_ok": False}
        titles = "\n".join(f"- {hit.title}" for hit in state["hits"][:15])
        result = await deps.llm.parse(
            system=GRADE_SYSTEM_PROMPT,
            user=f"Topic: {state['topic']}\n\nRetrieved paper titles:\n{titles}",
            schema=RelevanceGrade,
            max_tokens=300,
        )
        deps.usage.add(result.usage)
        grade = result.output
        assert isinstance(grade, RelevanceGrade)
        return {"relevance_ok": grade.relevant}

    async def refine_query(state: AgentState) -> dict:
        result = await deps.llm.parse(
            system=REFINE_SYSTEM_PROMPT,
            user=f"Topic: {state['topic']}\nPrevious query: {state['current_query']}",
            schema=RefinedQuery,
            max_tokens=200,
        )
        deps.usage.add(result.usage)
        refined = result.output
        assert isinstance(refined, RefinedQuery)
        return {
            "current_query": refined.query,
            "refine_count": state.get("refine_count", 0) + 1,
        }

    async def synthesize(state: AgentState) -> dict:
        payload, allowed_ids, new_papers, rebuilt = await deps.synthesize_fn(
            state["topic"], state["hits"]
        )
        return {
            "payload": payload,
            "allowed_ids": allowed_ids,
            "new_papers": new_papers,
            "rebuilt": rebuilt,
        }

    async def finalize(state: AgentState) -> dict:
        outcome = await deps.finalize_fn(state)
        if isinstance(outcome, BuildResult):
            return {"result": outcome}
        return {"refusal": outcome}

    def after_validate(state: AgentState) -> str:
        return "refused" if state.get("refusal") else "ok"

    def after_cache(state: AgentState) -> str:
        return "hit" if state.get("cache_hit") else "miss"

    def after_grade(state: AgentState) -> str:
        if state.get("relevance_ok"):
            return "good"
        if state.get("refine_count", 0) < MAX_REFINES:
            return "refine"
        return "give_up"  # proceed with what we have rather than fail the build

    def traced(name: str, fn):
        async def wrapper(state: AgentState) -> dict:
            with get_tracer().span(f"agent.{name}"):
                return await fn(state)

        return wrapper

    builder = StateGraph(AgentState)
    builder.add_node("validate_input", traced("validate_input", validate_input))
    builder.add_node("check_cache", traced("check_cache", check_cache))
    builder.add_node("retrieve", traced("retrieve", retrieve))
    builder.add_node("grade_relevance", traced("grade_relevance", grade_relevance))
    builder.add_node("refine_query", traced("refine_query", refine_query))
    builder.add_node("synthesize", traced("synthesize", synthesize))
    builder.add_node("finalize", traced("finalize", finalize))

    builder.set_entry_point("validate_input")
    builder.add_conditional_edges(
        "validate_input", after_validate, {"refused": END, "ok": "check_cache"}
    )
    builder.add_conditional_edges(
        "check_cache", after_cache, {"hit": END, "miss": "retrieve"}
    )
    builder.add_edge("retrieve", "grade_relevance")
    builder.add_conditional_edges(
        "grade_relevance",
        after_grade,
        {"good": "synthesize", "refine": "refine_query", "give_up": "synthesize"},
    )
    builder.add_edge("refine_query", "retrieve")
    builder.add_edge("synthesize", "finalize")
    builder.add_edge("finalize", END)
    return builder.compile()
