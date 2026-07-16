from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.db import init_db
from src.routers import health, ingest


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="ScholarScope API", version="0.1.0", lifespan=lifespan)
    app.include_router(health.router, tags=["health"])
    app.include_router(ingest.router, tags=["ingestion"])
    return app


app = create_app()
