from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.db import init_db
from src.routers import health, ingest, search
from src.services.retrieval.indexing import ensure_index
from src.services.retrieval.os_client import get_os_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await ensure_index(get_os_client())
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="ScholarScope API", version="0.1.0", lifespan=lifespan)
    app.include_router(health.router, tags=["health"])
    app.include_router(ingest.router, tags=["ingestion"])
    app.include_router(search.router, tags=["search"])
    return app


app = create_app()
