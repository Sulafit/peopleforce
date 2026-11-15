import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from peopleforce.modules.freelancer.models import FreelancerAsset, FreelancerProfile
from peopleforce.modules.onboarding.quiz import PersonalizationProfile


class FreelancerService:
    """Profile and asset persistence. Callers own the transaction (no commits here)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_profile(self, user_id: uuid.UUID) -> FreelancerProfile | None:
        return await self._session.get(FreelancerProfile, user_id)

    async def upsert_from_personalization(
        self, user_id: uuid.UUID, personalization: PersonalizationProfile, path_id: str
    ) -> None:
        """Create the profile, or refresh its quiz-derived fields. Avatar and name are left alone."""
        values = {
            "learning_path_id": path_id,
            "domain": personalization.domain,
            "specialization": personalization.specialization,
            "experience_level": personalization.experience_level,
            "freelance_stage": personalization.freelance_stage,
            "existing_assets": personalization.existing_assets,
            "acquisition_channel": personalization.acquisition_channel,
            "primary_goal": personalization.primary_goal,
        }
        stmt = insert(FreelancerProfile).values(user_id=user_id, **values)
        await self._session.execute(
            stmt.on_conflict_do_update(index_elements=[FreelancerProfile.user_id], set_=values)
        )

    async def save_asset(
        self,
        *,
        user_id: uuid.UUID,
        asset_type: str,
        lesson_id: str,
        action_key: str,
        content: dict[str, Any],
        origin: str = "user",
        status: str = "approved",
    ) -> tuple[FreelancerAsset, bool]:
        """Upsert the asset for one source action. Returns (asset, created)."""
        existing = await self._session.scalar(
            select(FreelancerAsset)
            .where(
                FreelancerAsset.user_id == user_id,
                FreelancerAsset.asset_type == asset_type,
                FreelancerAsset.source_lesson_id == lesson_id,
                FreelancerAsset.source_action_key == action_key,
            )
            .with_for_update()
        )
        if existing:
            if existing.content != content or existing.status != status:
                existing.content = content
                existing.status = status
                existing.origin = origin
                existing.revision += 1
            return existing, False
        asset = FreelancerAsset(
            user_id=user_id,
            asset_type=asset_type,
            source_lesson_id=lesson_id,
            source_action_key=action_key,
            content=content,
            origin=origin,
            status=status,
        )
        self._session.add(asset)
        await self._session.flush()
        return asset, True

    async def get_asset(self, user_id: uuid.UUID, asset_id: uuid.UUID) -> FreelancerAsset | None:
        asset = await self._session.get(FreelancerAsset, asset_id)
        return asset if asset and asset.user_id == user_id else None

    async def find_asset(self, user_id: uuid.UUID, lesson_id: str, action_key: str) -> FreelancerAsset | None:
        return await self._session.scalar(
            select(FreelancerAsset).where(
                FreelancerAsset.user_id == user_id,
                FreelancerAsset.source_lesson_id == lesson_id,
                FreelancerAsset.source_action_key == action_key,
            )
        )

    async def list_assets(self, user_id: uuid.UUID, *, approved_only: bool = False) -> list[FreelancerAsset]:
        stmt = select(FreelancerAsset).where(FreelancerAsset.user_id == user_id)
        if approved_only:
            stmt = stmt.where(FreelancerAsset.status.in_(("approved", "published")))
        return list(await self._session.scalars(stmt.order_by(FreelancerAsset.created_at)))
