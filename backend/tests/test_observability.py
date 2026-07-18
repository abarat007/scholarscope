import pytest
from src.services.observability import Tracer


class FakeObservationCM:
    def __init__(self, on_exit=None):
        self.on_exit = on_exit
        self.exited = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.exited = True
        if self.on_exit:
            self.on_exit()
        return False  # never suppress


class FakeClient:
    def __init__(self, on_exit=None):
        self.last_cm: FakeObservationCM | None = None
        self._on_exit = on_exit

    def start_as_current_observation(self, **kwargs):
        self.last_cm = FakeObservationCM(self._on_exit)
        return self.last_cm


def _tracer_with(client) -> Tracer:
    t = Tracer.__new__(Tracer)  # bypass real Langfuse init
    t._client = client
    return t


def test_body_exception_propagates_unchanged_and_span_is_closed():
    client = FakeClient()
    tracer = _tracer_with(client)

    with pytest.raises(ValueError, match="boom"):
        with tracer.span("x"):
            raise ValueError("boom")

    assert client.last_cm is not None
    assert client.last_cm.exited is True  # span was cleanly closed


def test_span_start_failure_disables_tracing_without_breaking_body():
    class ExplodingClient:
        def start_as_current_observation(self, **kwargs):
            raise RuntimeError("sdk drift")

    tracer = _tracer_with(ExplodingClient())
    ran = False
    with tracer.span("x") as span:
        ran = True
        assert span is None
    assert ran
    assert tracer.enabled is False  # disabled after the failure


def test_span_exit_failure_is_swallowed():
    tracer = _tracer_with(FakeClient(on_exit=lambda: (_ for _ in ()).throw(RuntimeError("x"))))
    # Body succeeds; a failing __exit__ must not surface.
    with tracer.span("x"):
        pass
    assert tracer.enabled is False


def test_disabled_tracer_yields_none():
    tracer = _tracer_with(None)
    with tracer.span("x") as span:
        assert span is None
    with tracer.generation("g", "model") as gen:
        assert gen is None
