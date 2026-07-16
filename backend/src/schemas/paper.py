from datetime import datetime

from pydantic import BaseModel


class ArxivPaper(BaseModel):
    """A paper as parsed from the arXiv Atom API, before persistence."""

    arxiv_id: str  # canonical id without version suffix, e.g. "2401.12345"
    version: int
    title: str
    abstract: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published_at: datetime
    updated_at: datetime
    pdf_url: str
