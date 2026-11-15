"""Runs AI capabilities. Supporting role only: nothing here decides progress or rewards."""

import json
import time
import uuid
from datetime import timedelta
from typing import Any

import structlog
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from peopleforce.core.config import Settings
from peopleforce.core.errors import AppError
from peopleforce.core.security import utcnow
from peopleforce.infrastructure.ai.prompts import PromptStore
from peopleforce.infrastructure.ai.providers import LlmError, LlmProvider
from peopleforce.modules.ai.capabilities import CAPABILITIES
from peopleforce.modules.ai.models import AiGeneration
from peopleforce.modules.freelancer.models import FreelancerProfile
from peopleforce.modules.freelancer.service import FreelancerService
from peopleforce.modules.onboarding import quiz

log = structlog.get_logger()


def learner_facts(profile: FreelancerProfile) -> dict[str, Any]:
    """The explicit quiz answers, as readable labels. The only personal context the model receives."""
    return {
        "specialization": quiz.label("specialization", profile.specialization),
        "experience": quiz.label("experience_level", profile.experience_level),
        "freelance_stage": quiz.label("freelance_stage", profile.freelance_stage),
        "already_has": [quiz.label("existing_assets", a) for a in profile.existing_assets],
        "preferred_channel": quiz.label("acquisition_channel", profile.acquisition_channel),
        "goal": quiz.label("primary_goal", profile.primary_goal),
    }


def _trace_input(payload: dict[str, Any]) -> Any:
    """What the trace shows at a glance. A whole document is summarized, not copied, into the root."""
    if "submission" in payload:
        return payload["submission"]
    if "document" in payload:
        return {"document": f"{len(payload['document'])} characters (contacts redacted)"}
    return payload


class AiService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        provider: LlmProvider | None,
        prompts: PromptStore,
        freelancer: FreelancerService,
    ) -> None:
        self._session = session
        self._settings = settings
        self._provider = provider
        self._prompts = prompts
        self._freelancer = freelancer

    @property
    def available(self) -> bool:
        return self._provider is not None

    async def run(
        self,
        *,
        user_id: uuid.UUID,
        capability_name: str,
        payload: dict[str, Any],
        lesson_id: str | None = None,
        action_key: str | None = None,
    ) -> tuple[dict[str, Any], uuid.UUID]:
        """Execute one capability. Returns (validated output, generation id).

        Raises AppError with a recoverable code; the caller's own writes are untouched because this
        method only ever commits its audit row.
        """
        capability = CAPABILITIES.get(capability_name)
        if capability is None:
            raise AppError("ai_capability_unknown", "This AI feature is not available.", 409)
        if self._provider is None:
            raise AppError("ai_not_configured", "AI feedback is not available right now.", 503)
        await self._enforce_daily_limit(user_id)

        profile = await self._freelancer.get_profile(user_id)
        context: dict[str, Any] = {"learner": learner_facts(profile) if profile else {}}
        if capability.context_asset_types:
            assets = await self._freelancer.list_assets(user_id, approved_only=True)
            context["approved_assets"] = [
                {"type": a.asset_type, "content": a.content}
                for a in assets
                if a.asset_type in capability.context_asset_types
            ]
        context.update(payload)

        prompt = await self._prompts.resolve(capability.prompt_name, capability.prompt_label)
        user_message = json.dumps(context, ensure_ascii=False)
        record = AiGeneration(
            user_id=user_id,
            capability=capability.name,
            prompt_name=prompt.name,
            prompt_version=prompt.version,
            model=self._provider.model,
            lesson_id=lesson_id,
            action_key=action_key,
            status="failed",
            input=context,
        )
        started = time.monotonic()
        messages = [{"role": "system", "content": prompt.text}, {"role": "user", "content": user_message}]
        try:
            with self._prompts.trace(
                name=capability.trace_name,
                # What a reviewer needs at a glance: the learner's own text for feedback, the task for drafts.
                input=_trace_input(payload),
                user_id=str(user_id),
                # Repeated requests on one exercise form one session: iterations on a draft read as a thread.
                session_id=f"{user_id}:{lesson_id}" if lesson_id else None,
                tags=[f"ai-{capability.kind}", capability.name],
                metadata={
                    "capability": capability.name,
                    "lesson_id": lesson_id or "",
                    "action_key": action_key or "",
                    "prompt_version": prompt.version,
                },
            ) as root:
                record.trace_id = self._prompts.current_trace_id()
                try:
                    with self._prompts.generation(
                        name=f"generate-{'feedback' if capability.kind == 'feedback' else 'draft'}",
                        model=self._provider.model,
                        prompt=prompt,
                        messages=messages,
                        model_parameters={
                            "max_output_tokens": capability.max_tokens,
                            "response_format": "json_schema",
                        },
                    ) as generation:
                        try:
                            result = await self._provider.generate_structured(
                                system=prompt.text,
                                user=user_message,
                                output_model=capability.output_model,
                                max_tokens=capability.max_tokens,
                                timeout=capability.timeout_seconds or self._settings.llm_timeout_seconds,
                            )
                        except (LlmError, ValidationError) as exc:
                            generation.update(level="ERROR", status_message=str(exc)[:500])
                            raise
                        output = result.output.model_dump(mode="json")
                        generation.update(
                            output={"role": "assistant", "content": json.dumps(output, ensure_ascii=False)},
                            usage_details=result.usage or None,
                            metadata={"thinking": result.thinking} if result.thinking else None,
                        )
                except (LlmError, ValidationError) as exc:
                    root.update(level="ERROR", status_message=str(exc)[:500])
                    raise
                root.update(output=output)
        except (LlmError, ValidationError) as exc:
            record.error = str(exc)[:1000]
            record.latency_ms = int((time.monotonic() - started) * 1000)
            self._session.add(record)
            await self._session.commit()
            log.warning("ai_generation_failed", capability=capability.name, error=record.error)
            retryable = getattr(exc, "retryable", True)
            raise AppError(
                "ai_unavailable",
                "AI feedback did not work this time. Your work is saved; you can try again or continue.",
                503,
                {"retryable": retryable},
            ) from exc

        record.status = "succeeded"
        record.output = output
        record.latency_ms = int((time.monotonic() - started) * 1000)
        self._session.add(record)
        await self._session.flush()
        return output, record.id

    async def _enforce_daily_limit(self, user_id: uuid.UUID) -> None:
        used = await self._session.scalar(
            select(func.count())
            .select_from(AiGeneration)
            .where(AiGeneration.user_id == user_id, AiGeneration.created_at > utcnow() - timedelta(days=1))
        )
        if (used or 0) >= self._settings.ai_daily_limit_per_user:
            raise AppError(
                "ai_limit_reached", "You've reached today's AI limit. It resets within 24 hours.", 429
            )
