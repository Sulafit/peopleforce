"""Action handlers: one function per action type, looked up in a registry.

A handler validates the learner's payload against the action's (already validated) configuration and
reports whether the action's completion strategy is now satisfied. Handlers never award XP, unlock
lessons or commit; the progression engine does that from the recorded outcomes.

Adding an action type = a Pydantic model in curriculum/schemas.py + a handler registered here.
"""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from peopleforce.core.errors import AppError
from peopleforce.modules.ai.service import AiService
from peopleforce.modules.curriculum.schemas import (
    AcknowledgeAction,
    Action,
    AiReviewAction,
    ExternalTaskAction,
    Lesson,
    QuizAction,
    SaveAssetAction,
    TextSubmissionAction,
)
from peopleforce.modules.freelancer.service import FreelancerService


@dataclass(frozen=True)
class ActionState:
    """Current state of one action for one learner (derived from its newest attempt)."""

    completed: bool = False
    payload: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    updated_at: datetime | None = None


@dataclass
class ActionContext:
    user_id: uuid.UUID
    lesson: Lesson | None  # None for daily challenges, which only use lesson-free action types
    action: Action
    payload: dict[str, Any]
    states: dict[str, ActionState]
    freelancer: FreelancerService
    ai: AiService


@dataclass
class ActionOutcome:
    completed: bool
    payload: dict[str, Any] = field(default_factory=dict)  # normalized input, stored
    result: dict[str, Any] = field(default_factory=dict)  # stored and returned to the learner
    asset_created: bool = False


Handler = Callable[[ActionContext], Awaitable[ActionOutcome]]


def invalid(message: str, fields: dict[str, str] | None = None) -> AppError:
    return AppError("invalid_submission", message, 422, {"fields": fields or {}})


def _source_values(ctx: ActionContext, source_key: str) -> dict[str, str]:
    source = ctx.states.get(source_key)
    if not source or not source.completed:
        raise AppError("dependency_not_met", "Save your draft first.", 409, {"requires": [source_key]})
    return dict(source.payload.get("values", {}))


async def acknowledge(ctx: ActionContext) -> ActionOutcome:
    assert isinstance(ctx.action, AcknowledgeAction)
    return ActionOutcome(completed=True)


async def text_submission(ctx: ActionContext) -> ActionOutcome:
    action = ctx.action
    assert isinstance(action, TextSubmissionAction)
    raw = ctx.payload.get("values")
    if not isinstance(raw, dict):
        raise invalid("Fill in the form to continue.")
    values: dict[str, str] = {}
    errors: dict[str, str] = {}
    for spec in action.fields:
        value = raw.get(spec.name, "")
        if not isinstance(value, str):
            errors[spec.name] = "Enter text."
            continue
        value = value.strip()
        if len(value) < spec.min_length:
            errors[spec.name] = (
                "This answer is required." if not value else f"Write at least {spec.min_length} characters."
            )
        elif len(value) > spec.max_length:
            errors[spec.name] = f"Keep it under {spec.max_length} characters."
        values[spec.name] = value
    if errors:
        raise invalid("Some answers need another look.", errors)
    return ActionOutcome(completed=True, payload={"values": values})


async def quiz(ctx: ActionContext) -> ActionOutcome:
    action = ctx.action
    assert isinstance(action, QuizAction)
    raw = ctx.payload.get("answers")
    if not isinstance(raw, dict):
        raise invalid("Answer every question.")
    answers: dict[str, str] = {}
    review: list[dict[str, Any]] = []
    correct = 0
    for question in action.questions:
        chosen = raw.get(question.id)
        if chosen not in {o.id for o in question.options}:
            raise invalid("Answer every question.", {question.id: "Choose one option."})
        answers[question.id] = chosen
        is_correct = chosen == question.correct_option_id
        correct += is_correct
        review.append(
            {
                "question_id": question.id,
                "correct": is_correct,
                "correct_option_id": question.correct_option_id,
                "explanation": question.explanation,
            }
        )
    total = len(action.questions)
    score = correct / total
    passed = score >= action.passing_score
    return ActionOutcome(
        completed=passed,
        payload={"answers": answers},
        result={
            "score": round(score, 3),
            "correct": correct,
            "total": total,
            "passed": passed,
            "review": review,
        },
    )


async def ai_review(ctx: ActionContext) -> ActionOutcome:
    action = ctx.action
    assert isinstance(action, AiReviewAction) and ctx.lesson is not None
    values = _source_values(ctx, action.source_action_key)
    source = ctx.lesson.action(action.source_action_key)
    assert isinstance(source, TextSubmissionAction)
    submission = [{"question": spec.label, "answer": values.get(spec.name, "")} for spec in source.fields]
    output, generation_id = await ctx.ai.run(
        user_id=ctx.user_id,
        capability_name=action.capability,
        lesson_id=ctx.lesson.id,
        action_key=action.key,
        payload={
            "exercise": {"lesson": ctx.lesson.title, "task": source.title, "goal": ctx.lesson.output},
            "submission": submission,
        },
    )
    return ActionOutcome(
        completed=True,
        payload={"source_action_key": action.source_action_key},
        result={"feedback": output, "generation_id": str(generation_id)},
    )


async def save_asset(ctx: ActionContext) -> ActionOutcome:
    action = ctx.action
    assert isinstance(action, SaveAssetAction) and ctx.lesson is not None
    values = _source_values(ctx, action.source_action_key)
    source = ctx.lesson.action(action.source_action_key)
    assert isinstance(source, TextSubmissionAction)
    content = {
        "fields": [
            {"name": spec.name, "label": spec.label, "value": values.get(spec.name, "")}
            for spec in source.fields
        ]
    }
    asset, created = await ctx.freelancer.save_asset(
        user_id=ctx.user_id,
        asset_type=action.asset_type,
        lesson_id=ctx.lesson.id,
        action_key=action.key,
        content=content,
    )
    return ActionOutcome(
        completed=True,
        payload={"source_action_key": action.source_action_key},
        result={"asset_id": str(asset.id), "asset_type": asset.asset_type, "revision": asset.revision},
        asset_created=created,
    )


async def external_task(ctx: ActionContext) -> ActionOutcome:
    """Self-reported progress on a real-world task. Partial counts are saved; the target completes it."""
    action = ctx.action
    assert isinstance(action, ExternalTaskAction)
    count = ctx.payload.get("count")
    if not isinstance(count, int) or isinstance(count, bool) or not 0 <= count <= action.target_count:
        raise invalid(f"Enter a number from 0 to {action.target_count}.")
    return ActionOutcome(
        completed=count >= action.target_count,
        payload={"count": count},
        result={"count": count, "target": action.target_count},
    )


HANDLERS: dict[str, Handler] = {
    "acknowledge": acknowledge,
    "text_submission": text_submission,
    "quiz": quiz,
    "ai_review": ai_review,
    "save_asset": save_asset,
    "external_task": external_task,
}
