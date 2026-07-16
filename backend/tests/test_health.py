from fastapi.testclient import TestClient
from src.config import Settings
from src.main import create_app
from src.routers import health as health_module


async def _ok(settings: Settings) -> str:
    return "stub detail"


async def _fail(settings: Settings) -> str:
    raise RuntimeError("connection refused")


def test_liveness_needs_no_dependencies():
    client = TestClient(create_app())
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "alive"}


def test_health_ok_when_all_dependencies_healthy(monkeypatch):
    monkeypatch.setattr(health_module, "CHECKS", {"postgres": _ok, "redis": _ok})
    client = TestClient(create_app())

    body = client.get("/health").json()

    assert body["status"] == "ok"
    assert {dep["name"] for dep in body["dependencies"]} == {"postgres", "redis"}
    assert all(dep["healthy"] for dep in body["dependencies"])


def test_health_degraded_identifies_failing_dependency(monkeypatch):
    monkeypatch.setattr(
        health_module, "CHECKS", {"postgres": _ok, "opensearch": _fail}
    )
    client = TestClient(create_app())

    body = client.get("/health").json()

    assert body["status"] == "degraded"
    failing = next(dep for dep in body["dependencies"] if dep["name"] == "opensearch")
    assert failing["healthy"] is False
    assert "connection refused" in failing["detail"]
    healthy = next(dep for dep in body["dependencies"] if dep["name"] == "postgres")
    assert healthy["healthy"] is True
