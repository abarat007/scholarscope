"""Shared pipeline helpers for the landscape agent."""

from src.models.paper import Paper
from src.schemas.paper import ArxivPaper


def row_to_schema(row: Paper) -> ArxivPaper:
    return ArxivPaper(
        arxiv_id=row.arxiv_id,
        version=row.version,
        title=row.title,
        abstract=row.abstract,
        authors=row.authors,
        categories=row.categories,
        primary_category=row.primary_category,
        published_at=row.published_at,
        updated_at=row.updated_at,
        pdf_url=row.pdf_url,
    )
