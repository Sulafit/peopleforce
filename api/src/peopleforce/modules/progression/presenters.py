"""Learner-facing views of content. Strips anything the client must not see (quiz answers) and
applies deterministic personalization (examples and wording chosen from the quiz profile)."""

from typing import Any

from peopleforce.infrastructure.ai.prompts import render
from peopleforce.modules.actions.handlers import ActionState
from peopleforce.modules.ai.capabilities import CAPABILITIES
from peopleforce.modules.curriculum.schemas import (
    AcknowledgeAction,
    Action,
    ActionGroupBlock,
    AiReviewAction,
    Block,
    CalloutBlock,
    DocumentReviewAction,
    ExternalTaskAction,
    Lesson,
    MarkdownBlock,
    QuizAction,
    ResourcesBlock,
    SaveAssetAction,
    TextSubmissionAction,
    YouTubeBlock,
)
from peopleforce.modules.freelancer.models import FreelancerProfile
from peopleforce.modules.onboarding import quiz
from peopleforce.modules.progression import engine
from peopleforce.modules.progression.schemas import ActionOut, ActionStateOut

MAX_DOCUMENT_MEGABYTES = 5


def personalization_tokens(profile: FreelancerProfile) -> dict[str, str]:
    """The only variables content may reference, as {{name}}."""
    return {
        "role": quiz.ROLE.get(profile.specialization, "software developer"),
        "specialization": quiz.label("specialization", profile.specialization),
        "goal": quiz.label("primary_goal", profile.primary_goal).lower(),
        "channel": quiz.label("acquisition_channel", profile.acquisition_channel),
    }


def block_view(block: Block, profile: FreelancerProfile) -> dict[str, Any]:
    tokens = personalization_tokens(profile)
    if isinstance(block, MarkdownBlock):
        return {
            "type": block.type,
            "key": block.key,
            "title": block.title,
            "body": render(block.body, tokens),
        }
    if isinstance(block, YouTubeBlock):
        return {
            "type": block.type,
            "key": block.key,
            "title": block.title,
            "video_id": block.video_id,
            "points": list(block.points),
        }
    if isinstance(block, CalloutBlock):
        body = block.body_by_specialization.get(profile.specialization, block.body)
        return {
            "type": block.type,
            "key": block.key,
            "tone": block.tone,
            "title": block.title,
            "body": render(body, tokens),
        }
    if isinstance(block, ResourcesBlock):
        return {
            "type": block.type,
            "key": block.key,
            "title": block.title,
            "links": [link.model_dump() for link in block.links],
        }
    assert isinstance(block, ActionGroupBlock)
    return {
        "type": block.type,
        "key": block.key,
        "title": block.title,
        "intro": render(block.intro, tokens) if block.intro else None,
        "action_keys": list(block.action_keys),
    }


def action_config(action: Action, profile: FreelancerProfile) -> dict[str, Any]:
    if isinstance(action, AcknowledgeAction):
        return {"confirm_label": action.confirm_label}
    if isinstance(action, TextSubmissionAction):
        return {
            "submit_label": action.submit_label,
            "fields": [
                {
                    "name": f.name,
                    "label": f.label,
                    "help": f.help,
                    "placeholder": f.placeholder,
                    "multiline": f.multiline,
                    "min_length": f.min_length,
                    "max_length": f.max_length,
                    "example": f.examples.get(profile.specialization) or f.examples.get("default"),
                }
                for f in action.fields
            ],
        }
    if isinstance(action, QuizAction):
        # correct_option_id and explanations are deliberately omitted; they come back after an attempt.
        return {
            "passing_score": action.passing_score,
            "questions": [
                {"id": q.id, "prompt": q.prompt, "options": [o.model_dump() for o in q.options]}
                for q in action.questions
            ],
        }
    if isinstance(action, AiReviewAction):
        capability = CAPABILITIES.get(action.capability)
        return {
            "source_action_key": action.source_action_key,
            "submit_label": action.submit_label,
            "supported": capability is not None and capability.kind == "feedback",
        }
    if isinstance(action, DocumentReviewAction):
        return {
            "submit_label": action.submit_label,
            "min_score": action.min_score,
            "max_megabytes": MAX_DOCUMENT_MEGABYTES,
        }
    if isinstance(action, ExternalTaskAction):
        return {"target_count": action.target_count, "unit": action.unit, "tips": list(action.tips)}
    assert isinstance(action, SaveAssetAction)
    return {
        "asset_type": action.asset_type,
        "source_action_key": action.source_action_key,
        "submit_label": action.submit_label,
    }


def action_view(
    lesson: Lesson, action: Action, states: dict[str, ActionState], profile: FreelancerProfile
) -> ActionOut:
    state = states.get(action.key, ActionState())
    return ActionOut(
        key=action.key,
        type=action.type,
        title=action.title,
        instructions=action.instructions,
        required=action.required,
        config=action_config(action, profile),
        blocked_by=engine.unmet_dependencies(lesson, action.key, states),
        state=ActionStateOut(
            completed=state.completed,
            payload=state.payload,
            result=state.result,
            updated_at=state.updated_at,
            stale=engine.is_stale(lesson, action.key, states),
        ),
    )
