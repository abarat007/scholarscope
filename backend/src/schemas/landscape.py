from typing import Literal

from pydantic import BaseModel, Field

from src.schemas.extraction import PaperExtraction


class ClusterInfo(BaseModel):
    id: int
    name: str
    description: str
    paper_ids: list[str]
    centroid: list[float]


class Relationship(BaseModel):
    source_cluster_id: int
    target_cluster_id: int
    description: str


class LandscapePayload(BaseModel):
    """The persisted landscape document for one topic (stored as JSONB)."""

    topic: str
    version: int
    embedding_model: str
    extraction_schema_version: int
    clusters: list[ClusterInfo]
    relationships: list[Relationship]
    tensions: list[str]
    open_problems: list[str]
    # arxiv_id -> landscape version in which the paper first appeared;
    # powers "N new papers since your last visit" in the reading map.
    paper_versions: dict[str, int]


# --- LLM output schemas -------------------------------------------------


class ClusterDescription(BaseModel):
    name: str = Field(description="A specific 2-6 word name for this research cluster")
    description: str = Field(description="Two or three sentences on what unites these papers")


class CrossClusterAnalysis(BaseModel):
    relationships: list[Relationship] = Field(
        description="How clusters build on, enable, or compete with each other"
    )
    tensions: list[str] = Field(
        description="Genuine methodological or empirical disagreements across the clusters"
    )
    open_problems: list[str] = Field(
        description="Concrete unsolved problems the field acknowledges"
    )


# --- Graph response -----------------------------------------------------


class GraphNode(BaseModel):
    id: str
    type: Literal["cluster", "paper"]
    label: str
    cluster_id: int | None = None
    added_in_version: int | None = None


class GraphEdge(BaseModel):
    source: str
    target: str
    type: Literal["membership", "relationship"]
    label: str | None = None


class LandscapeGraph(BaseModel):
    topic: str
    version: int
    paper_count: int
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    tensions: list[str]
    open_problems: list[str]


class BuildResult(BaseModel):
    topic: str
    version: int
    papers: int
    new_papers: int
    clusters: int
    rebuilt: bool
    input_tokens: int
    output_tokens: int
    cost_usd: float


class PaperCard(BaseModel):
    arxiv_id: str
    title: str
    extraction: PaperExtraction | None
