"""Langfuse tracing, degrading to a no-op when unconfigured.

All Langfuse SDK usage is isolated here: the rest of the codebase talks to
`Tracer`, which yields None spans when keys are absent (tests, CI, or a stack
running without observability).
"""

import logging
from contextlib import contextmanager

from src.config import get_settings

log = logging.getLogger(__name__)


class Tracer:
    def __init__(self):
        settings = get_settings()
        self._client = None
        if settings.langfuse_public_key and settings.langfuse_secret_key:
            try:
                from langfuse import Langfuse

                self._client = Langfuse(
                    public_key=settings.langfuse_public_key,
                    secret_key=settings.langfuse_secret_key,
                    host=settings.langfuse_host or "http://localhost:3000",
                )
                log.info("langfuse tracing enabled (%s)", settings.langfuse_host)
            except Exception:
                log.exception("langfuse init failed; tracing disabled")

    @property
    def enabled(self) -> bool:
        return self._client is not None

    @contextmanager
    def span(self, name: str, **metadata):
        if self._client is None:
            yield None
            return
        with self._client.start_as_current_span(
            name=name, metadata=metadata or None
        ) as span:
            yield span

    @contextmanager
    def generation(self, name: str, model: str):
        if self._client is None:
            yield None
            return
        with self._client.start_as_current_generation(name=name, model=model) as gen:
            yield gen

    def flush(self) -> None:
        if self._client is not None:
            self._client.flush()


_tracer: Tracer | None = None


def get_tracer() -> Tracer:
    global _tracer
    if _tracer is None:
        _tracer = Tracer()
    return _tracer
