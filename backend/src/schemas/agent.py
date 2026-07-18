from typing import Literal

from pydantic import BaseModel, Field


class RelevanceGrade(BaseModel):
    relevant: bool = Field(
        description="True if most of the retrieved papers plausibly address the topic"
    )
    reason: str


class RefinedQuery(BaseModel):
    query: str = Field(description="A reformulated search query likely to retrieve better papers")


class RefusalResponse(BaseModel):
    refused: Literal[True] = True
    rail: str
    reason: str
    message: str
