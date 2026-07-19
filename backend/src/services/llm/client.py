"""Provider-agnostic structured-output LLM wrapper.

The rest of the codebase depends only on `StructuredLLM.parse(...)` returning
a validated Pydantic model plus token usage — swapping providers means one new
adapter class here, nothing else.
"""

from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel

from src.config import get_settings

ModelT = TypeVar("ModelT", bound=BaseModel)


@dataclass
class LLMUsage:
    input_tokens: int = 0
    output_tokens: int = 0

    def add(self, other: "LLMUsage") -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens

    def cost_usd(self, input_per_mtok: float, output_per_mtok: float) -> float:
        return round(
            self.input_tokens / 1e6 * input_per_mtok
            + self.output_tokens / 1e6 * output_per_mtok,
            6,
        )


@dataclass
class LLMResult:
    output: BaseModel
    usage: LLMUsage


class StructuredLLM(Protocol):
    async def parse(
        self, *, system: str, user: str, schema: type[ModelT], max_tokens: int
    ) -> LLMResult: ...


class AnthropicLLM:
    """Claude via the Anthropic SDK's structured-output parse API."""

    def __init__(self, model: str | None = None):
        import anthropic  # lazy: only the live path needs the SDK configured

        self._client = anthropic.AsyncAnthropic()
        self._model = model or get_settings().claude_model

    async def parse(
        self, *, system: str, user: str, schema: type[ModelT], max_tokens: int = 2000
    ) -> LLMResult:
        from src.services.observability import get_tracer

        tracer = get_tracer()
        with tracer.generation(name=f"parse:{schema.__name__}", model=self._model) as gen:
            # Disable extended thinking for structured extraction. On Sonnet 5
            # omitting `thinking` runs adaptive thinking, which consumes the
            # max_tokens budget before the JSON is emitted and truncates it.
            # These schema-constrained calls don't need it — the schema is the
            # structure — and disabling keeps token budgets predictable.
            response = await self._client.messages.parse(
                model=self._model,
                max_tokens=max_tokens,
                thinking={"type": "disabled"},
                system=system,
                messages=[{"role": "user", "content": user}],
                output_format=schema,
            )
            if response.parsed_output is None:
                raise RuntimeError(
                    f"structured output parse failed (stop_reason={response.stop_reason})"
                )
            usage = LLMUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )
            tracer.update_generation(
                gen, input_tokens=usage.input_tokens, output_tokens=usage.output_tokens
            )
            return LLMResult(output=response.parsed_output, usage=usage)


_llm: StructuredLLM | None = None


def get_llm() -> StructuredLLM:
    global _llm
    if _llm is None:
        _llm = AnthropicLLM()
    return _llm
