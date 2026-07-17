"""OpenSearch index management and bulk indexing for papers."""

import json

import httpx

from src.config import get_settings
from src.schemas.paper import ArxivPaper

INDEX_NAME = "papers"


def index_definition(embedding_model: str, embedding_dims: int) -> dict:
    """Full index body: BM25 text fields + a k-NN vector field.

    The embedding model and dimension are recorded in mapping _meta so any
    future re-embedding is traceable to what the index was built with.
    """
    return {
        "settings": {
            "index": {
                "knn": True,
                "number_of_shards": 1,
                "number_of_replicas": 0,  # single-node cluster
            }
        },
        "mappings": {
            "_meta": {
                "embedding_model": embedding_model,
                "embedding_dims": embedding_dims,
            },
            "properties": {
                "arxiv_id": {"type": "keyword"},
                "title": {"type": "text"},
                "abstract": {"type": "text"},
                "authors": {"type": "keyword"},
                "categories": {"type": "keyword"},
                "primary_category": {"type": "keyword"},
                "published_at": {"type": "date"},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": embedding_dims,
                    "method": {
                        "name": "hnsw",
                        "engine": "lucene",
                        "space_type": "cosinesimil",
                    },
                },
            },
        },
    }


async def ensure_index(client: httpx.AsyncClient, index: str = INDEX_NAME) -> bool:
    """Create the index if missing. Returns True when newly created."""
    head = await client.head(f"/{index}")
    if head.status_code == 200:
        return False
    settings = get_settings()
    resp = await client.put(
        f"/{index}", json=index_definition(settings.embedding_model, settings.embedding_dims)
    )
    resp.raise_for_status()
    return True


async def bulk_index_papers(
    client: httpx.AsyncClient,
    papers: list[ArxivPaper],
    embeddings: list[list[float]],
    *,
    index: str = INDEX_NAME,
    refresh: bool = False,
) -> int:
    """Bulk-upsert papers into OpenSearch, keyed on arxiv_id."""
    if len(papers) != len(embeddings):
        raise ValueError("papers and embeddings must be the same length")
    if not papers:
        return 0

    lines: list[str] = []
    for paper, vector in zip(papers, embeddings, strict=True):
        lines.append(json.dumps({"index": {"_index": index, "_id": paper.arxiv_id}}))
        lines.append(
            json.dumps(
                {
                    "arxiv_id": paper.arxiv_id,
                    "title": paper.title,
                    "abstract": paper.abstract,
                    "authors": paper.authors,
                    "categories": paper.categories,
                    "primary_category": paper.primary_category,
                    "published_at": paper.published_at.isoformat(),
                    "embedding": vector,
                }
            )
        )
    resp = await client.post(
        "/_bulk",
        params={"refresh": "true"} if refresh else None,
        content="\n".join(lines) + "\n",
        headers={"Content-Type": "application/x-ndjson"},
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("errors"):
        first_error = next(
            item["index"]["error"] for item in body["items"] if item["index"].get("error")
        )
        raise RuntimeError(f"bulk indexing reported errors, first: {first_error}")
    return len(papers)
