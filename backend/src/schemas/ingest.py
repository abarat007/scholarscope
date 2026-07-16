from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    category: str = Field(pattern=r"^[a-z-]+(\.[A-Za-z-]+)?$", examples=["cs.CL"])
    days_back: int = Field(default=2, ge=1, le=30)
    max_results: int = Field(default=200, ge=1, le=1000)


class IngestResult(BaseModel):
    category: str
    fetched: int
    within_window: int
    inserted: int
    updated: int
