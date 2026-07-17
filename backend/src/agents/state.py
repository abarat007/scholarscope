from typing import TypedDict

from src.schemas.landscape import BuildResult, LandscapePayload
from src.schemas.search import SearchHit


class AgentState(TypedDict, total=False):
    """Typed state threaded through the landscape agent graph."""

    query: str  # original user input
    current_query: str  # possibly refined during the loop
    topic: str  # canonical topic after semantic-cache resolution
    paper_count: int

    refusal: dict | None  # set by input rails or output check; terminal
    cache_hit: bool

    hits: list[SearchHit]
    relevance_ok: bool
    refine_count: int

    payload: LandscapePayload  # unsaved synthesis output
    allowed_ids: set[str]  # retrieved now + previously in the landscape
    new_papers: int
    rebuilt: bool

    result: BuildResult  # final, persisted outcome
