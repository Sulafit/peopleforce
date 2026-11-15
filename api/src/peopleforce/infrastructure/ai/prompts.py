"""Prompt lookup and tracing (Langfuse).

Langfuse is the primary prompt store when configured. A versioned copy of every prompt is committed
under modules/ai/prompts/ so development and outages do not depend on Langfuse being reachable.

Tracing follows Langfuse's "what does a good trace look like" guidance:
  * one trace per AI task, named verb-first and stable (`review-freelance-offer`);
  * the root observation carries what a reviewer reads at a glance (the learner's text in, the result out);
  * the model call is a `generation` with model, parameters, token usage and the linked prompt version;
  * user, session, tags and metadata are propagated to every observation in the trace.
Tracing must never break a request: with no client configured every method is a no-op.
"""

import asyncio
import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger()

PROMPT_DIR = Path(__file__).resolve().parents[2] / "modules" / "ai" / "prompts"
_VERSION_LINE = re.compile(r"^version:\s*(\S+)\s*$")


@dataclass(frozen=True)
class ResolvedPrompt:
    name: str
    version: str  # "langfuse:<n>" or "local:<n>"
    text: str
    # The Langfuse prompt object, when the text came from Langfuse. Links the generation to the version.
    langfuse_prompt: Any = None


def load_local_prompt(name: str) -> ResolvedPrompt:
    """Local prompt file: first line `version: <n>`, a blank line, then the prompt text."""
    raw = (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")
    first, _, rest = raw.partition("\n")
    match = _VERSION_LINE.match(first)
    if not match:
        raise ValueError(f"prompt {name} is missing its `version:` header")
    return ResolvedPrompt(name=name, version=f"local:{match.group(1)}", text=rest.strip())


class _NoopObservation:
    def update(self, **_: Any) -> None:
        return None


class PromptStore:
    def __init__(
        self, public_key: str = "", secret_key: str = "", host: str = "", environment: str = ""
    ) -> None:
        self._client: Any = None
        self._environment = environment or None
        if public_key and secret_key:
            try:
                from langfuse import Langfuse

                self._client = Langfuse(
                    public_key=public_key, secret_key=secret_key, host=host, environment=environment or None
                )
            except Exception as exc:
                log.warning("langfuse_init_failed", error=str(exc))

    @property
    def tracing_enabled(self) -> bool:
        return self._client is not None

    async def resolve(self, name: str, label: str) -> ResolvedPrompt:
        local = load_local_prompt(name)
        if self._client is None:
            return local
        try:
            prompt = await asyncio.to_thread(
                self._client.get_prompt, name, label=label, fallback=local.text, fetch_timeout_seconds=3
            )
            if getattr(prompt, "is_fallback", False):
                return local
            return ResolvedPrompt(
                name=name, version=f"langfuse:{prompt.version}", text=prompt.prompt, langfuse_prompt=prompt
            )
        except Exception as exc:
            log.warning("langfuse_prompt_fetch_failed", prompt=name, error=str(exc))
            return local

    @contextmanager
    def trace(
        self,
        *,
        name: str,
        input: Any,
        user_id: str,
        session_id: str | None,
        tags: list[str],
        metadata: dict[str, str],
    ) -> Iterator[Any]:
        """One trace for one AI task. Yields the root observation (or a no-op)."""
        if self._client is None:
            yield _NoopObservation()
            return
        from langfuse import propagate_attributes

        # Attributes set here are inherited by every observation created inside the block.
        with propagate_attributes(
            trace_name=name,
            user_id=user_id,
            session_id=session_id,
            tags=tags,
            # Empty values say nothing; leaving them out keeps metadata filters clean.
            metadata={key: value for key, value in metadata.items() if value},
            environment=self._environment,
        ):
            with self._client.start_as_current_observation(as_type="span", name=name, input=input) as root:
                yield root

    @contextmanager
    def generation(
        self,
        *,
        name: str,
        model: str,
        prompt: ResolvedPrompt,
        messages: list[dict[str, str]],
        model_parameters: dict[str, str | int | float | bool],
    ) -> Iterator[Any]:
        """The model call itself, as a `generation` nested under the current trace."""
        if self._client is None:
            yield _NoopObservation()
            return
        with self._client.start_as_current_observation(
            as_type="generation",
            name=name,
            model=model,
            input=messages,
            model_parameters=model_parameters,
            prompt=prompt.langfuse_prompt,
            metadata={"prompt_name": prompt.name, "prompt_version": prompt.version},
        ) as observation:
            yield observation

    def current_trace_id(self) -> str | None:
        if self._client is None:
            return None
        try:
            return self._client.get_current_trace_id()
        except Exception:
            return None

    def shutdown(self) -> None:
        """Flush queued spans. Called when the app stops, so nothing is lost on deploy."""
        if self._client is not None:
            try:
                self._client.shutdown()
            except Exception:
                pass


def render(template: str, variables: dict[str, str]) -> str:
    """Fill {{name}} placeholders. Unknown placeholders are left as-is."""
    return re.sub(r"\{\{\s*(\w+)\s*\}\}", lambda m: variables.get(m.group(1), m.group(0)), template)
