from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.db import init_db
from src.routers import health, ingest, landscape, papers, search
from src.services.retrieval.indexing import ensure_index
from src.services.retrieval.os_client import get_os_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await ensure_index(get_os_client())
    yield
    from src.services.observability import get_tracer

    get_tracer().flush()


def create_app() -> FastAPI:
    app = FastAPI(title="ScholarScope API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, tags=["health"])
    app.include_router(ingest.router, tags=["ingestion"])
    app.include_router(search.router, tags=["search"])
    app.include_router(landscape.router, tags=["landscape"])
    app.include_router(papers.router, tags=["papers"])
    return app


app = create_app()
