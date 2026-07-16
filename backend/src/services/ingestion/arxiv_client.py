"""Minimal arXiv Atom API client.

arXiv's terms ask for at most one request every three seconds, so all requests
go through an async rate limiter. Transient failures (5xx, transport errors)
are retried with exponential backoff; client errors are not.
"""

import asyncio
import re
import time
import xml.etree.ElementTree as ET
from collections.abc import Awaitable, Callable
from datetime import datetime

import httpx

from src.schemas.paper import ArxivPaper

ARXIV_API_URL = "https://export.arxiv.org/api/query"
MIN_REQUEST_INTERVAL_S = 3.0

_ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}
_VERSION_RE = re.compile(r"v(\d+)$")

Clock = Callable[[], float]
Sleep = Callable[[float], Awaitable[None]]


class AsyncRateLimiter:
    """Enforces a minimum interval between acquisitions across concurrent callers."""

    def __init__(
        self,
        min_interval_s: float,
        *,
        clock: Clock = time.monotonic,
        sleep: Sleep = asyncio.sleep,
    ):
        self._min_interval = min_interval_s
        self._clock = clock
        self._sleep = sleep
        self._lock = asyncio.Lock()
        self._last_acquired: float | None = None

    async def acquire(self) -> None:
        async with self._lock:
            if self._last_acquired is not None:
                wait = self._min_interval - (self._clock() - self._last_acquired)
                if wait > 0:
                    await self._sleep(wait)
            self._last_acquired = self._clock()


# One limiter for the whole process: concurrent requests (e.g. the three DAG
# category tasks) must share the 1-request-per-3s budget arXiv grants per client.
_shared_rate_limiter = AsyncRateLimiter(MIN_REQUEST_INTERVAL_S)


def _split_versioned_id(raw: str) -> tuple[str, int]:
    match = _VERSION_RE.search(raw)
    if match:
        return raw[: match.start()], int(match.group(1))
    return raw, 1


def _normalize_ws(text: str) -> str:
    return " ".join(text.split())


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_atom_feed(xml_text: str) -> list[ArxivPaper]:
    """Parse an arXiv Atom feed into papers. Pure function, no I/O."""
    root = ET.fromstring(xml_text)
    papers: list[ArxivPaper] = []
    for entry in root.findall("atom:entry", _ATOM_NS):
        raw_id = entry.findtext("atom:id", default="", namespaces=_ATOM_NS)
        # ids look like http://arxiv.org/abs/2401.12345v2 (or legacy cs/0301012v1)
        arxiv_id, version = _split_versioned_id(raw_id.split("/abs/")[-1])
        if not arxiv_id:
            continue

        categories = [
            term
            for c in entry.findall("atom:category", _ATOM_NS)
            if (term := c.get("term"))
        ]
        primary_el = entry.find("arxiv:primary_category", _ATOM_NS)
        primary = primary_el.get("term") if primary_el is not None else None

        pdf_url = next(
            (
                link.get("href")
                for link in entry.findall("atom:link", _ATOM_NS)
                if link.get("title") == "pdf"
            ),
            f"https://arxiv.org/pdf/{arxiv_id}",
        )

        papers.append(
            ArxivPaper(
                arxiv_id=arxiv_id,
                version=version,
                title=_normalize_ws(entry.findtext("atom:title", default="", namespaces=_ATOM_NS)),
                abstract=_normalize_ws(
                    entry.findtext("atom:summary", default="", namespaces=_ATOM_NS)
                ),
                authors=[
                    name
                    for a in entry.findall("atom:author", _ATOM_NS)
                    if (name := a.findtext("atom:name", default="", namespaces=_ATOM_NS))
                ],
                categories=categories,
                primary_category=primary or (categories[0] if categories else "unknown"),
                published_at=_parse_timestamp(
                    entry.findtext("atom:published", default="", namespaces=_ATOM_NS)
                ),
                updated_at=_parse_timestamp(
                    entry.findtext("atom:updated", default="", namespaces=_ATOM_NS)
                ),
                pdf_url=pdf_url or f"https://arxiv.org/pdf/{arxiv_id}",
            )
        )
    return papers


class ArxivClient:
    def __init__(
        self,
        http: httpx.AsyncClient | None = None,
        *,
        rate_limiter: AsyncRateLimiter | None = None,
        max_retries: int = 4,
        backoff_base_s: float = 3.0,
        sleep: Sleep = asyncio.sleep,
    ):
        self._http = http or httpx.AsyncClient(timeout=30.0)
        self._owns_http = http is None
        self._rate_limiter = rate_limiter or _shared_rate_limiter
        self._max_retries = max_retries
        self._backoff_base_s = backoff_base_s
        self._sleep = sleep

    async def search(
        self,
        query: str,
        *,
        start: int = 0,
        max_results: int = 100,
        sort_by: str = "submittedDate",
        sort_order: str = "descending",
    ) -> list[ArxivPaper]:
        """Run one search request; page by advancing `start`."""
        xml_text = await self._get_with_retry(
            {
                "search_query": query,
                "start": start,
                "max_results": max_results,
                "sortBy": sort_by,
                "sortOrder": sort_order,
            }
        )
        return parse_atom_feed(xml_text)

    async def _get_with_retry(self, params: dict) -> str:
        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            await self._rate_limiter.acquire()
            try:
                resp = await self._http.get(ARXIV_API_URL, params=params)
                resp.raise_for_status()
                return resp.text
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status < 500 and status != 429:
                    raise  # client errors are our bug; retrying won't help
                last_exc = exc  # 429 (rate limited) and 5xx are retryable
            except httpx.TransportError as exc:
                last_exc = exc
            await self._sleep(self._backoff_base_s * 2**attempt)
        assert last_exc is not None
        raise last_exc

    async def aclose(self) -> None:
        if self._owns_http:
            await self._http.aclose()
