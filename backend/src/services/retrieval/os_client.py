"""Thin async OpenSearch REST client.

Deliberately httpx-based rather than an SDK wrapper: every query this project
sends is explicit request JSON, which keeps BM25/k-NN scoring internals
visible and debuggable.
"""

import httpx

from src.config import get_settings

_client: httpx.AsyncClient | None = None


def get_os_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(base_url=get_settings().opensearch_url, timeout=30.0)
    return _client
