"""Reciprocal Rank Fusion, implemented by hand.

RRF(d) = sum over rankings r of 1 / (k + rank_r(d)), rank starting at 1.
The constant k (default 60, from Cormack et al. 2009) damps the dominance of
top ranks so agreement between rankings outweighs a single high placement.
Scores are comparable only within one fusion call — never across queries.
"""

from collections.abc import Sequence

DEFAULT_K = 60


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[str]], *, k: int = DEFAULT_K
) -> list[tuple[str, float]]:
    """Fuse ranked id lists into one ranking. Deterministic: ties break by id."""
    if k < 1:
        raise ValueError("k must be >= 1")
    scores: dict[str, float] = {}
    for ranking in rankings:
        seen: set[str] = set()
        for rank, doc_id in enumerate(ranking, start=1):
            if doc_id in seen:
                continue  # a malformed ranking must not double-count a doc
            seen.add(doc_id)
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))
