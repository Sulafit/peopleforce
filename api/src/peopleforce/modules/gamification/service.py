import uuid
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from peopleforce.modules.curriculum.schemas import (
    Achievement,
    AssetCreatedTrigger,
    LearningPath,
    LessonCompletedTrigger,
    LessonsCompletedCountTrigger,
)
from peopleforce.modules.freelancer.models import FreelancerAsset
from peopleforce.modules.gamification.models import ActivityDay, UserAchievement, XpEvent
from peopleforce.modules.gamification.ranks import Streak, compute_streak
from peopleforce.modules.progression.models import LessonProgress


class GamificationService:
    """XP ledger and achievements. Callers own the transaction (no commits here)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def award_xp(
        self, user_id: uuid.UUID, amount: int, reason: str, source_id: str, idempotency_key: str
    ) -> bool:
        """Append an XP event once. Returns False when this reward was already paid."""
        inserted = (
            await self._session.execute(
                insert(XpEvent)
                .values(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    amount=amount,
                    reason=reason,
                    source_id=source_id,
                    idempotency_key=idempotency_key,
                )
                .on_conflict_do_nothing(index_elements=[XpEvent.user_id, XpEvent.idempotency_key])
                .returning(XpEvent.id)
            )
        ).first()
        return inserted is not None

    async def total_xp(self, user_id: uuid.UUID) -> int:
        total = await self._session.scalar(
            select(func.coalesce(func.sum(XpEvent.amount), 0)).where(XpEvent.user_id == user_id)
        )
        return int(total or 0)

    async def earned(self, user_id: uuid.UUID) -> dict[str, datetime]:
        rows = await self._session.execute(
            select(UserAchievement.achievement_key, UserAchievement.earned_at).where(
                UserAchievement.user_id == user_id
            )
        )
        return {row.achievement_key: row.earned_at for row in rows}

    async def evaluate_achievements(self, user_id: uuid.UUID, path: LearningPath) -> list[Achievement]:
        """Grant every achievement whose trigger now holds. Returns the newly earned ones."""
        already = await self.earned(user_id)
        candidates = [a for a in path.achievements if a.key not in already]
        if not candidates:
            return []

        completed = set(
            await self._session.scalars(
                select(LessonProgress.lesson_id).where(
                    LessonProgress.user_id == user_id, LessonProgress.status == "completed"
                )
            )
        )
        asset_types = set(
            await self._session.scalars(
                select(FreelancerAsset.asset_type).where(
                    FreelancerAsset.user_id == user_id,
                    FreelancerAsset.status.in_(("approved", "published")),
                )
            )
        )

        newly: list[Achievement] = []
        for achievement in candidates:
            trigger = achievement.trigger
            if isinstance(trigger, LessonCompletedTrigger):
                met = trigger.lesson_id in completed
            elif isinstance(trigger, LessonsCompletedCountTrigger):
                met = len(completed) >= trigger.count
            elif isinstance(trigger, AssetCreatedTrigger):
                met = trigger.asset_type in asset_types
            else:  # pragma: no cover - the discriminated union is exhaustive
                met = False
            if not met:
                continue
            inserted = (
                await self._session.execute(
                    insert(UserAchievement)
                    .values(user_id=user_id, achievement_key=achievement.key)
                    .on_conflict_do_nothing()
                    .returning(UserAchievement.achievement_key)
                )
            ).first()
            if inserted is not None:
                newly.append(achievement)
        return newly

    async def record_activity(self, user_id: uuid.UUID, day: date) -> None:
        """Mark a local day as active. Idempotent."""
        await self._session.execute(
            insert(ActivityDay).values(user_id=user_id, day=day).on_conflict_do_nothing()
        )

    async def active_days(self, user_id: uuid.UUID, since: date | None = None) -> set[date]:
        stmt = select(ActivityDay.day).where(ActivityDay.user_id == user_id)
        if since is not None:
            stmt = stmt.where(ActivityDay.day >= since)
        return set(await self._session.scalars(stmt))

    async def streak(self, user_id: uuid.UUID, today: date) -> tuple[Streak, list[tuple[date, bool]]]:
        """Current and longest streak, plus the last seven days for the week strip."""
        days = await self.active_days(user_id)
        week = [
            (today - timedelta(days=offset), (today - timedelta(days=offset)) in days)
            for offset in range(6, -1, -1)
        ]
        return compute_streak(days, today), week
