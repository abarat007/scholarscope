"""One-shot corpus backfill: page through arXiv results for a query and upsert.

Run inside the backend container (it has network + DB access):

    docker compose exec backend python -m src.services.ingestion.backfill \
        --query 'all:"retrieval augmented generation"' --max-papers 2000

Paging respects the arXiv rate limit (1 request / 3s), so ~2k papers takes
about a minute. Re-running is safe — upserts are idempotent on arxiv_id.
"""

import argparse
import asyncio
import sys

from src.db import get_session_factory, init_db
from src.services.ingestion.arxiv_client import ArxivClient
from src.services.ingestion.repository import upsert_papers


async def backfill(query: str, max_papers: int, page_size: int) -> tuple[int, int]:
    await init_db()
    client = ArxivClient()
    total_inserted = total_updated = 0
    try:
        async with get_session_factory()() as session:
            for start in range(0, max_papers, page_size):
                page = await client.search(
                    query, start=start, max_results=min(page_size, max_papers - start)
                )
                if not page:
                    print(f"no more results at offset {start}; stopping")
                    break
                inserted, updated = await upsert_papers(session, page)
                total_inserted += inserted
                total_updated += updated
                print(
                    f"page offset={start}: fetched={len(page)} "
                    f"inserted={inserted} updated={updated} "
                    f"(total {total_inserted + total_updated})"
                )
    finally:
        await client.aclose()
    return total_inserted, total_updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill papers from arXiv")
    parser.add_argument(
        "--query",
        required=True,
        help="raw arXiv search_query, e.g. 'cat:cs.CL' or 'all:\"retrieval augmented generation\"'",
    )
    parser.add_argument("--max-papers", type=int, default=2000)
    parser.add_argument("--page-size", type=int, default=200)
    args = parser.parse_args()

    inserted, updated = asyncio.run(backfill(args.query, args.max_papers, args.page_size))
    print(f"backfill complete: inserted={inserted} updated={updated}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
