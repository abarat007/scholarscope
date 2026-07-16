from fastapi import FastAPI

from src.routers import health


def create_app() -> FastAPI:
    app = FastAPI(title="ScholarScope API", version="0.1.0")
    app.include_router(health.router, tags=["health"])
    return app


app = create_app()
