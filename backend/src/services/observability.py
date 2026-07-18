"""Langfuse tracing, degrading to a no-op when unconfigured or on any error.

All Langfuse SDK usage is isolated here. Two hard rules:
  1. Tracing must never break a request — every SDK call is guarded, and any
     failure disables the tracer and yields a None span.
  2. The rest of the codebase talks only to `Tracer`, so an SDK API change is
     contained to this file.
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
                self._client = None

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def _disable(self, exc: Exception) -> None:
        log.warning("langfuse tracing error; disabling for this process: %s", exc)
        self._client = None

    @contextmanager
    def _observation(self, name: str, as_type: str, **kwargs):
        if self._client is None:
            yield None
            return
        try:
            cm = self._client.start_as_current_observation(
                name=name, as_type=as_type, **kwargs
            )
        except Exception as exc:  # SDK API drift or transport issue
            self._disable(exc)
            yield None
            return
        try:
            with cm as observation:
                yield observation
        except Exception as exc:
            # Never let a tracing failure escape into the request path.
            self._disable(exc)
            yield None

    def span(self, name: str, **metadata):
        return self._observation(name, "span", metadata=metadata or None)

    def generation(self, name: str, model: str):
        return self._observation(name, "generation", model=model)

    def update_generation(self, observation, *, input_tokens: int, output_tokens: int) -> None:
        if observation is None or self._client is None:
            return
        try:
            observation.update(usage_details={"input": input_tokens, "output": output_tokens})
        except Exception as exc:
            self._disable(exc)

    def flush(self) -> None:
        if self._client is not None:
            try:
                self._client.flush()
            except Exception as exc:
                self._disable(exc)


_tracer: Tracer | None = None


def get_tracer() -> Tracer:
    global _tracer
    if _tracer is None:
        _tracer = Tracer()
    return _tracer
