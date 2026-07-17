from pydantic import BaseModel, Field

# Bump when the schema or extraction prompt changes materially: the Redis
# cache key includes this, so stale-shaped extractions are never served.
EXTRACTION_SCHEMA_VERSION = 1


class PaperExtraction(BaseModel):
    """Structured reading of a single paper (from title + abstract in v1)."""

    problem: str = Field(description="The problem the paper addresses, one or two sentences")
    method: str = Field(description="The approach or technique proposed")
    results: str = Field(description="Key results or findings; 'not stated' if absent")
    contribution: str = Field(description="The main novel contribution")
    limitations: str = Field(
        description="Stated or evident limitations; 'not stated' if the abstract gives none"
    )
    key_terms: list[str] = Field(description="3-8 technical terms central to the paper")
