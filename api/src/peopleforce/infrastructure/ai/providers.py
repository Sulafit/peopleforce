"""LLM provider abstraction. The rest of the app only knows `LlmProvider`."""

import asyncio
from dataclasses import dataclass, field
from typing import Protocol, TypeVar

import anthropic
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LlmError(Exception):
    """Any provider failure. `retryable` tells the caller whether trying again can help."""

    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass(frozen=True)
class LlmResult[T: BaseModel]:
    """A validated answer plus what observability needs: token usage and any reasoning summary."""

    output: T
    # Keys follow Langfuse usage details: input_tokens, output_tokens, optionally reasoning_tokens.
    usage: dict[str, int] = field(default_factory=dict)
    thinking: str | None = None


class LlmProvider(Protocol):
    name: str
    model: str

    async def generate_structured(
        self, *, system: str, user: str, output_model: type[T], max_tokens: int, timeout: float
    ) -> LlmResult[T]:
        """Return a validated instance of `output_model` with usage, or raise LlmError."""
        ...


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, model: str) -> None:
        self.model = model
        # Credentials are resolved by the SDK (ANTHROPIC_API_KEY or an `ant auth login` profile).
        self._client = anthropic.AsyncAnthropic()

    async def generate_structured(
        self, *, system: str, user: str, output_model: type[T], max_tokens: int, timeout: float
    ) -> LlmResult[T]:
        try:
            response = await self._client.with_options(timeout=timeout, max_retries=1).messages.parse(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_format=output_model,
            )
        except anthropic.RateLimitError as exc:
            raise LlmError("provider rate limit") from exc
        except anthropic.APIStatusError as exc:
            raise LlmError(f"provider error {exc.status_code}", retryable=exc.status_code >= 500) from exc
        except anthropic.APIConnectionError as exc:  # includes timeouts
            raise LlmError("provider unreachable") from exc

        if response.stop_reason == "refusal":
            raise LlmError("the model declined this request", retryable=False)
        if response.stop_reason == "max_tokens" or response.parsed_output is None:
            raise LlmError("the model returned an incomplete answer")
        usage = {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}
        return LlmResult(output=response.parsed_output, usage=usage)


class GeminiProvider:
    name = "gemini"

    def __init__(self, model: str, api_key: str) -> None:
        from google import genai

        self.model = model
        self._client = genai.Client(api_key=api_key)

    async def generate_structured(
        self, *, system: str, user: str, output_model: type[T], max_tokens: int, timeout: float
    ) -> LlmResult[T]:
        from google.genai import errors, types

        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=output_model,
            max_output_tokens=max_tokens,
            http_options=types.HttpOptions(timeout=int(timeout * 1000)),
        )
        response = None
        for attempt in (1, 2):  # one retry: "model overloaded" (503) is usually gone a moment later
            try:
                response = await self._client.aio.models.generate_content(
                    model=self.model, contents=user, config=config
                )
                break
            except errors.APIError as exc:
                code = exc.code or 0
                transient = code == 429 or code >= 500
                if transient and attempt == 1:
                    await asyncio.sleep(1.5)
                    continue
                raise LlmError(f"provider error {code}", retryable=transient) from exc
            except Exception as exc:  # network errors and timeouts surface as transport exceptions
                raise LlmError(f"provider unreachable: {type(exc).__name__}") from exc
        assert response is not None

        text = response.text
        if not text:
            raise LlmError("the model returned no answer", retryable=False)

        usage: dict[str, int] = {}
        meta = response.usage_metadata
        if meta is not None:
            reasoning = meta.thoughts_token_count or 0
            usage = {
                "input_tokens": meta.prompt_token_count or 0,
                # Thinking tokens are billed as output, so they are counted there and also shown apart.
                "output_tokens": (meta.candidates_token_count or 0) + reasoning,
            }
            if reasoning:
                usage["reasoning_tokens"] = reasoning
        # Validate ourselves: the model's JSON is untrusted input like any other.
        return LlmResult(output=output_model.model_validate_json(text), usage=usage)
