"""AI-generated platform drafts. Output is stored as a `draft` asset until the learner approves it."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from peopleforce.core.errors import AppError, not_found
from peopleforce.infrastructure.analytics.base import Analytics
from peopleforce.modules.ai.capabilities import platform_for_channel
from peopleforce.modules.ai.service import AiService
from peopleforce.modules.auth.schemas import CurrentUser
from peopleforce.modules.freelancer.models import FreelancerAsset
from peopleforce.modules.freelancer.schemas import AssetOut, GenerateDraftOut, asset_out
from peopleforce.modules.freelancer.service import FreelancerService

GENERATED_SOURCE = "generated"


class AssetDraftService:
    def __init__(
        self, session: AsyncSession, freelancer: FreelancerService, ai: AiService, analytics: Analytics
    ) -> None:
        self._session = session
        self._freelancer = freelancer
        self._ai = ai
        self._analytics = analytics

    async def list_assets(self, user: CurrentUser) -> list[AssetOut]:
        return [asset_out(a) for a in await self._freelancer.list_assets(user.id)]

    async def generate_platform_draft(self, user: CurrentUser) -> GenerateDraftOut:
        profile = await self._freelancer.get_profile(user.id)
        if profile is None:
            raise AppError("onboarding_required", "Finish the short quiz to set up your journey.", 409)
        approved = await self._freelancer.list_assets(user.id, approved_only=True)
        if not any(a.asset_type == "freelancer_offer" for a in approved):
            raise AppError(
                "offer_required", "Save your freelance offer first; the draft is written from it.", 409
            )
        platform = platform_for_channel(profile.acquisition_channel)
        output, _ = await self._ai.run(
            user_id=user.id,
            capability_name="generate_platform_draft",
            payload={"platform": {"name": platform.label, "format_requirements": platform.requirements}},
        )
        asset, created = await self._freelancer.save_asset(
            user_id=user.id,
            asset_type=platform.asset_type,
            lesson_id=GENERATED_SOURCE,
            action_key=platform.key,
            content={"platform": platform.key, **output},
            origin="ai",
            status="draft",
        )
        await self._session.commit()
        await self._session.refresh(asset)
        if created:
            self._analytics.capture(
                str(user.id), "freelancer_asset_created", {"asset_type": asset.asset_type, "origin": "ai"}
            )
        return GenerateDraftOut(asset=asset_out(asset), platform_label=platform.label)

    async def _owned_draft(self, user: CurrentUser, asset_id: uuid.UUID) -> FreelancerAsset:
        asset = await self._freelancer.get_asset(user.id, asset_id)
        if asset is None:
            raise not_found("Asset")
        if asset.source_lesson_id != GENERATED_SOURCE:
            raise AppError("asset_not_editable", "Edit this in the lesson that created it.", 409)
        return asset

    async def update_draft(self, user: CurrentUser, asset_id: uuid.UUID, title: str, body: str) -> AssetOut:
        asset = await self._owned_draft(user, asset_id)
        title, body = title.strip(), body.strip()
        if not title or not body or len(title) > 300 or len(body) > 6000:
            raise AppError("invalid_submission", "Title and text are required.", 422)
        asset.content = {**asset.content, "title": title, "body": body}
        asset.origin = "user"  # the learner has rewritten it
        asset.status = "draft"
        asset.revision += 1
        await self._session.commit()
        await self._session.refresh(asset)
        return asset_out(asset)

    async def approve(self, user: CurrentUser, asset_id: uuid.UUID) -> AssetOut:
        asset = await self._owned_draft(user, asset_id)
        if asset.status == "draft":
            asset.status = "approved"
            asset.revision += 1
            await self._session.commit()
            await self._session.refresh(asset)
            self._analytics.capture(
                str(user.id), "freelancer_asset_approved", {"asset_type": asset.asset_type}
            )
        return asset_out(asset)
