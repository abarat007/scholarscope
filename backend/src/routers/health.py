import asyncio
import time
from collections.abc import Awaitable, Callable

import asyncpg
import httpx
import redis.asyncio as aioredis
from fastapi import APIRouter

from src.config import Settings, get_settings
from src.schemas.health import DependencyStatus, HealthResponse

router = APIRouter()

CHECK_TIMEOUT_S = 3.0

Check = Callable[[Settings], Awaitable[str | None]]


async def check_postgres(settings: Settings) -> str | None:
    conn = await asyncpg.connect(dsn=settings.postgres_dsn, timeout=CHECK_TIMEOUT_S)
    try:
        await conn.fetchval("SELECT 1")
    finally:
        await conn.close()
    return None


async def check_opensearch(settings: Settings) -> str | None:
    async with httpx.AsyncClient(timeout=CHECK_TIMEOUT_S) as client:
        resp = await client.get(f"{settings.opensearch_url}/_cluster/health")
        resp.raise_for_status()
        return f"cluster status: {resp.json().get('status', 'unknown')}"


async def check_redis(settings: Settings) -> str | None:
    client = aioredis.from_url(settings.redis_url, socket_timeout=CHECK_TIMEOUT_S)
    try:
        await client.ping()
    finally:
        await client.aclose()
    return None


async def check_langfuse(settings: Settings) -> str | None:
    if not settings.langfuse_host:
        return "not configured"
    async with httpx.AsyncClient(timeout=CHECK_TIMEOUT_S) as client:
        resp = await client.get(f"{settings.langfuse_host}/api/public/health")
        resp.raise_for_status()
        return None


async def check_airflow(settings: Settings) -> str | None:
    # Health path moved between Airflow major versions; accept either.
    async with httpx.AsyncClient(timeout=CHECK_TIMEOUT_S) as client:
        for path in ("/api/v2/monitor/health", "/health"):
            try:
                resp = await client.get(f"{settings.airflow_url}{path}")
            except httpx.HTTPError:
                continue
            if resp.status_code == 200:
                return None
    raise RuntimeError("no Airflow health endpoint responded")


CHECKS: dict[str, Check] = {
    "postgres": check_postgres,
    "opensearch": check_opensearch,
    "redis": check_redis,
    "airflow": check_airflow,
    "langfuse": check_langfuse,
}


async def _run_check(name: str, check: Check, settings: Settings) -> DependencyStatus:
    start = time.perf_counter()
    try:
        detail = await asyncio.wait_for(check(settings), timeout=CHECK_TIMEOUT_S + 1)
        healthy = True
    except Exception as exc:
        detail = f"{type(exc).__name__}: {exc}"
        healthy = False
    latency_ms = round((time.perf_counter() - start) * 1000, 1)
    return DependencyStatus(name=name, healthy=healthy, latency_ms=latency_ms, detail=detail)


@router.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    results = await asyncio.gather(
        *(_run_check(name, check, settings) for name, check in CHECKS.items())
    )
    status = "ok" if all(dep.healthy for dep in results) else "degraded"
    return HealthResponse(status=status, dependencies=list(results))
