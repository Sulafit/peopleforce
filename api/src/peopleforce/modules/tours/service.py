"""First-run tour: a small persisted state machine driven by semantic events.

    journey_intro -> first_lesson_started -> avatar_selection -> first_reward_claimed
                  -> next_lesson_prompt -> completed

The tour only *narrates* the first-run flow. Progress, rewards and the avatar step are owned by the
progression engine, so skipping the tour never blocks anything. `reconcile` re-derives the stage from
learning facts, which makes refreshes, logouts and out-of-order events harmless.
"""

import uuid
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from peopleforce.core.security import utcnow
from peopleforce.infrastructure.analytics.base import Analytics
from peopleforce.modules.tours.models import TourProgress

FIRST_RUN = "first_run"

STAGES = (
    "journey_intro",
    "first_lesson_started",
    "avatar_selection",
    "first_reward_claimed",
    "next_lesson_prompt",
    "completed",
)

ClientEvent = Literal[
    "first_lesson_opened", "reward_acknowledged", "next_prompt_acknowledged", "skip", "replay"
]
ServerEvent = Literal["first_lesson_submitted", "reward_claimed"]
FirstLessonFact = Literal["not_started", "in_progress", "reward_pending", "completed"]

TRANSITIONS: dict[tuple[str, str], str] = {
    ("journey_intro", "first_lesson_opened"): "first_lesson_started",
    ("journey_intro", "first_lesson_submitted"): "avatar_selection",
    ("first_lesson_started", "first_lesson_submitted"): "avatar_selection",
    ("avatar_selection", "reward_claimed"): "first_reward_claimed",
    ("first_reward_claimed", "reward_acknowledged"): "next_lesson_prompt",
    ("next_lesson_prompt", "next_prompt_acknowledged"): "completed",
}


def _index(stage: str) -> int:
    return STAGES.index(stage)


def stage_floor(fact: FirstLessonFact) -> str:
    """The earliest stage that is consistent with what the learner has actually done."""
    if fact == "completed":
        return "first_reward_claimed"
    if fact == "reward_pending":
        return "avatar_selection"
    return "journey_intro"


class TourService:
    """Callers own the transaction (no commits here)."""

    def __init__(self, session: AsyncSession, analytics: Analytics) -> None:
        self._session = session
        self._analytics = analytics

    async def get(self, user_id: uuid.UUID) -> TourProgress | None:
        return await self._session.get(TourProgress, (user_id, FIRST_RUN))

    async def get_or_start(self, user_id: uuid.UUID, fact: FirstLessonFact) -> TourProgress:
        tour = await self.get(user_id)
        if tour is None:
            tour = TourProgress(user_id=user_id, tour_key=FIRST_RUN, stage="journey_intro", status="active")
            self._session.add(tour)
            await self._session.flush()
            self._analytics.capture(str(user_id), "tour_started", {"tour": FIRST_RUN})
        self.reconcile(tour, fact)
        return tour

    @staticmethod
    def reconcile(tour: TourProgress, fact: FirstLessonFact) -> None:
        floor = stage_floor(fact)
        if tour.stage != "completed" and _index(tour.stage) < _index(floor):
            tour.stage = floor

    async def apply(self, user_id: uuid.UUID, event: str, fact: FirstLessonFact) -> TourProgress:
        """Apply one event. Unknown or out-of-order events are no-ops, so retries are safe."""
        tour = await self.get_or_start(user_id, fact)

        if event == "skip":
            if tour.status == "active":
                tour.status = "skipped"
                self._analytics.capture(str(user_id), "tour_skipped", {"stage": tour.stage})
            return tour

        if event == "replay":
            tour.status = "active"
            tour.completed_at = None
            # Resume where the facts say the learner is; a finished first lesson replays the last hint.
            tour.stage = "next_lesson_prompt" if fact == "completed" else stage_floor(fact)
            return tour

        target = TRANSITIONS.get((tour.stage, event))
        if target is None:
            return tour
        tour.stage = target
        if target == "completed":
            self._finish(tour)
        return tour

    def _finish(self, tour: TourProgress) -> None:
        was_active = tour.status == "active"
        tour.completed_at = utcnow()
        if was_active:
            tour.status = "completed"
            self._analytics.capture(str(tour.user_id), "tour_completed", {"tour": FIRST_RUN})
