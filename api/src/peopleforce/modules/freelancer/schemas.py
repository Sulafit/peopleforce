import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from peopleforce.modules.freelancer.models import FreelancerAsset, FreelancerProfile
from peopleforce.modules.onboarding import quiz


class ProfileOut(BaseModel):
    display_name: str | None
    avatar_key: str | None
    timezone: str
    domain: str
    specialization: str
    specialization_label: str
    role_label: str
    experience_level: str
    freelance_stage: str
    stage_label: str
    existing_assets: list[str]
    acquisition_channel: str
    channel_label: str
    primary_goal: str
    goal_label: str


def profile_out(profile: FreelancerProfile) -> ProfileOut:
    return ProfileOut(
        display_name=profile.display_name,
        avatar_key=profile.avatar_key,
        timezone=profile.timezone,
        domain=profile.domain,
        specialization=profile.specialization,
        specialization_label=quiz.label("specialization", profile.specialization),
        role_label=quiz.ROLE.get(profile.specialization, "software developer"),
        experience_level=profile.experience_level,
        freelance_stage=profile.freelance_stage,
        stage_label=quiz.label("freelance_stage", profile.freelance_stage),
        existing_assets=profile.existing_assets,
        acquisition_channel=profile.acquisition_channel,
        channel_label=quiz.label("acquisition_channel", profile.acquisition_channel),
        primary_goal=profile.primary_goal,
        goal_label=quiz.label("primary_goal", profile.primary_goal),
    )


class AssetOut(BaseModel):
    id: uuid.UUID
    asset_type: str
    source_lesson_id: str
    source_action_key: str
    content: dict[str, Any]
    status: str
    origin: str
    revision: int
    created_at: datetime
    updated_at: datetime


def asset_out(asset: FreelancerAsset) -> AssetOut:
    return AssetOut.model_validate(asset, from_attributes=True)


class GenerateDraftOut(BaseModel):
    asset: AssetOut
    platform_label: str


class AssetUpdateIn(BaseModel):
    title: str
    body: str
