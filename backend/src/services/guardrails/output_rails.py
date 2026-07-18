"""Output guardrails: every paper the synthesis cites must be real and retrieved.

A landscape may only reference arxiv_ids that were (a) in the retrieved set
for this run or already part of the landscape, and (b) present in Postgres.
Hallucinated ids are stripped; if too much of the payload was invalid the
result is rejected outright rather than silently repaired.
"""

from dataclasses import dataclass, field

from src.schemas.landscape import LandscapePayload

MAX_INVALID_FRACTION = 0.2


@dataclass
class OutputCheckResult:
    payload: LandscapePayload
    removed_paper_ids: list[str] = field(default_factory=list)
    rejected: bool = False
    reason: str | None = None


def check_output(
    payload: LandscapePayload,
    *,
    allowed_ids: set[str],
    known_ids: set[str],
) -> OutputCheckResult:
    """Validate and repair a landscape payload against ground truth.

    allowed_ids: papers legitimately in scope for this landscape (retrieved
    now or present in prior versions). known_ids: papers that exist in
    Postgres. A cited id must be in both.
    """
    valid = allowed_ids & known_ids
    cited = [pid for cluster in payload.clusters for pid in cluster.paper_ids]
    if not cited:
        return OutputCheckResult(payload, rejected=True, reason="landscape cites no papers")

    removed = [pid for pid in cited if pid not in valid]
    invalid_fraction = len(removed) / len(cited)
    if invalid_fraction > MAX_INVALID_FRACTION:
        return OutputCheckResult(
            payload,
            removed_paper_ids=removed,
            rejected=True,
            reason=(
                f"{len(removed)}/{len(cited)} cited papers failed verification "
                f"({invalid_fraction:.0%} > {MAX_INVALID_FRACTION:.0%})"
            ),
        )

    if not removed:
        return OutputCheckResult(payload)

    clusters = []
    for cluster in payload.clusters:
        kept = [pid for pid in cluster.paper_ids if pid in valid]
        if kept:
            clusters.append(cluster.model_copy(update={"paper_ids": kept}))
    surviving_cluster_ids = {c.id for c in clusters}
    relationships = [
        r
        for r in payload.relationships
        if r.source_cluster_id in surviving_cluster_ids
        and r.target_cluster_id in surviving_cluster_ids
    ]
    paper_versions = {
        pid: version for pid, version in payload.paper_versions.items() if pid in valid
    }
    repaired = payload.model_copy(
        update={
            "clusters": clusters,
            "relationships": relationships,
            "paper_versions": paper_versions,
        }
    )
    return OutputCheckResult(repaired, removed_paper_ids=removed)
