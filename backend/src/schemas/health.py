from typing import Literal

from pydantic import BaseModel


class DependencyStatus(BaseModel):
    name: str
    healthy: bool
    latency_ms: float
    detail: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    dependencies: list[DependencyStatus]
