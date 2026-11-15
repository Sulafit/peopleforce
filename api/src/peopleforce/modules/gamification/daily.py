"""Daily challenge: one short task per learner per local day, worth XP once, and it keeps the streak alive.

Challenges are content (`LearningPath.daily_challenges`). Which one a learner gets on a given day is a
deterministic rotation, so a refresh never changes it. Progress and XP rules are identical to lessons:
the action handler validates, the ledger pays exactly once (key `daily:<date>`).
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from peopleforce.core.errors import AppError
from peopleforce.core.security import utcnow
from peopleforce.infrastructure.analytics.base import Analytics
from peopleforce.modules.actions.handlers import HANDLERS, ActionContext, ActionState
from peopleforce.modules.ai.service import AiService
from peopleforce.modules.auth.schemas import CurrentUser
from peopleforce.modules.curriculum.schemas import DailyChallenge, LearningPath
from peopleforce.modules.curriculum.service import CurriculumService
from peopleforce.modules.freelancer.models import FreelancerProfile
from peopleforce.modules.freelancer.service import FreelancerService
from peopleforce.modules.gamification.models import DailyChallengeEntry
from peopleforce.modules.gamification.ranks import local_day, rank_for
from peopleforce.modules.gamification.schemas import rank_out, streak_out
from peopleforce.modules.gamification.service import GamificationService
from peopleforce.modules.progression.presenters import action_config
from peopleforce.modules.progression.schemas import (
    ActionOut,
    ActionStateOut,
    DailyChallengeOut,
    DailyOut,
    DailySubmitOut,
)


def pick_challenge(
    path: LearningPath, user_int: int, day: date, pinned_key: str | None
) -> DailyChallenge | None:
    """Today's challenge. An existing entry pins the choice; otherwise rotate through the pool."""
    pool = path.daily_challenges
    if not pool:
        return None
    if pinned_key:
        pinned = next((c for c in pool if c.key == pinned_key), None)
        if pinned:
            return pinned
    return pool[(day.toordinal() + user_int) % len(pool)]


class DailyService:
    def __init__(
        self,
        session: AsyncSession,
        curriculum: CurriculumService,
        freelancer: FreelancerService,
        gamification: GamificationService,
        ai: AiService,
        analytics: Analytics,
    ) -> None:
        self._session = session
        self._curriculum = curriculum
        self._freelancer = freelancer
        self._gamification = gamification
        self._ai = ai
        self._analytics = analytics

    async def _context(self, user: CurrentUser) -> tuple[FreelancerProfile, LearningPath, date]:
        profile = await self._freelancer.get_profile(user.id)
        if profile is None:
            raise AppError("onboarding_required", "Finish the short quiz to set up your journey.", 409)
        path = await self._curriculum.get_path_by_id(profile.learning_path_id)
        return profile, path, local_day(utcnow(), profile.timezone)

    async def _out(
        self,
        user: CurrentUser,
        profile: FreelancerProfile,
        day: date,
        challenge: DailyChallenge | None,
        entry: DailyChallengeEntry | None,
    ) -> DailyOut:
        streak = streak_out(*await self._gamification.streak(user.id, day))
        if challenge is None:
            return DailyOut(day=day.isoformat(), challenge=None, completed=False, streak=streak)
        action = challenge.action
        return DailyOut(
            day=day.isoformat(),
            completed=bool(entry and entry.completed),
            streak=streak,
            challenge=DailyChallengeOut(
                key=challenge.key,
                title=challenge.title,
                intro=challenge.intro,
                xp=challenge.xp,
                action=ActionOut(
                    key=action.key,
                    type=action.type,
                    title=action.title,
                    instructions=action.instructions,
                    required=True,
                    config=action_config(action, profile),
                    blocked_by=[],
                    state=ActionStateOut(
                        completed=bool(entry and entry.completed),
                        payload=entry.payload if entry else {},
                        result=entry.result if entry else {},
                        updated_at=entry.completed_at or entry.created_at if entry else None,
                        stale=False,
                    ),
                ),
            ),
        )

    async def today(self, user: CurrentUser) -> DailyOut:
        profile, path, day = await self._context(user)
        entry = await self._session.get(DailyChallengeEntry, (user.id, day))
        challenge = pick_challenge(path, user.id.int, day, entry.challenge_key if entry else None)
        return await self._out(user, profile, day, challenge, entry)

    async def submit(self, user: CurrentUser, payload: dict) -> DailySubmitOut:
        profile, path, day = await self._context(user)

        # Create-or-lock today's row so concurrent submissions run one after the other.
        first = pick_challenge(path, user.id.int, day, None)
        if first is None:
            raise AppError("daily_unavailable", "There is no daily challenge today.", 404)
        await self._session.execute(
            insert(DailyChallengeEntry)
            .values(user_id=user.id, day=day, challenge_key=first.key)
            .on_conflict_do_nothing()
        )
        entry = await self._session.scalar(
            select(DailyChallengeEntry)
            .where(DailyChallengeEntry.user_id == user.id, DailyChallengeEntry.day == day)
            .with_for_update()
        )
        assert entry is not None
        challenge = pick_challenge(path, user.id.int, day, entry.challenge_key) or first
        xp_before = await self._gamification.total_xp(user.id)

        paid = False
        if not entry.completed:
            outcome = await HANDLERS[challenge.action.type](
                ActionContext(
                    user_id=user.id,
                    lesson=None,
                    action=challenge.action,
                    payload=payload,
                    states={challenge.action.key: ActionState()},
                    freelancer=self._freelancer,
                    ai=self._ai,
                )
            )
            entry.challenge_key = challenge.key
            entry.payload = outcome.payload
            entry.result = outcome.result
            if outcome.completed:
                entry.completed = True
                entry.completed_at = utcnow()
                paid = await self._gamification.award_xp(
                    user.id, challenge.xp, "daily_challenge", challenge.key, f"daily:{day.isoformat()}"
                )
                await self._gamification.record_activity(user.id, day)
            await self._session.flush()

        xp_total = await self._gamification.total_xp(user.id)
        rank_up = rank_for(xp_total).number > rank_for(xp_before).number
        out = DailySubmitOut(
            daily=await self._out(user, profile, day, challenge, entry),
            xp_awarded=challenge.xp if paid else 0,
            xp_total=xp_total,
            rank=rank_out(xp_total),
            rank_up=rank_up,
        )
        await self._session.commit()
        if paid:
            self._analytics.capture(
                str(user.id),
                "daily_challenge_completed",
                {"challenge": challenge.key, "streak": out.daily.streak.current},
            )
            self._analytics.capture(str(user.id), "xp_awarded", {"source": "daily", "amount": challenge.xp})
        return out
