"""Progression engine: the only place that decides availability, completion and rewards.

Reward order for the very first lesson (the learner has no avatar yet):

    complete_lesson  -> lesson_progress.status = reward_pending   (work is saved, no XP yet)
    select_avatar    -> avatar saved + XP event + status = completed + achievements, in ONE transaction

Every other completion pays XP immediately. XP is paid through an idempotent ledger insert, so
repeated or concurrent calls can never pay twice.
"""

from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from peopleforce.core.errors import AppError, not_found
from peopleforce.core.security import utcnow
from peopleforce.infrastructure.analytics.base import Analytics
from peopleforce.modules.actions.handlers import HANDLERS, ActionContext, ActionState
from peopleforce.modules.ai.service import AiService
from peopleforce.modules.auth.schemas import CurrentUser
from peopleforce.modules.curriculum.schemas import Achievement, LearningPath, Lesson
from peopleforce.modules.curriculum.service import CurriculumService
from peopleforce.modules.freelancer.models import FreelancerProfile
from peopleforce.modules.freelancer.schemas import asset_out, profile_out
from peopleforce.modules.freelancer.service import FreelancerService
from peopleforce.modules.gamification.models import XpEvent
from peopleforce.modules.gamification.ranks import local_day, rank_for, valid_timezone
from peopleforce.modules.gamification.schemas import rank_ladder, rank_out, streak_out
from peopleforce.modules.gamification.service import GamificationService
from peopleforce.modules.onboarding import quiz
from peopleforce.modules.progression import engine
from peopleforce.modules.progression.models import ActionAttempt, LessonProgress, LessonSnapshot
from peopleforce.modules.progression.presenters import action_view, block_view
from peopleforce.modules.progression.schemas import (
    AchievementOut,
    ActionSubmitOut,
    AvatarOut,
    ChapterOut,
    CompleteOut,
    JourneyOut,
    LessonChapterOut,
    LessonNodeOut,
    LessonOut,
    LessonRef,
    PartOut,
    ProfilePageOut,
    RewardOut,
    TourOut,
)
from peopleforce.modules.tours.models import TourProgress
from peopleforce.modules.tours.service import FirstLessonFact, TourService

log = structlog.get_logger()


def xp_key(lesson_id: str) -> str:
    return f"lesson:{lesson_id}:completed"


def _tour_out(tour: TourProgress) -> TourOut:
    return TourOut(stage=tour.stage, status=tour.status)  # type: ignore[arg-type]


def _lesson_ref(lesson: Lesson | None) -> LessonRef | None:
    return LessonRef(id=lesson.id, title=lesson.title, playable=lesson.playable) if lesson else None


def _next_lesson(path: LearningPath, lesson_id: str) -> Lesson | None:
    lessons = path.lessons
    index = next((i for i, item in enumerate(lessons) if item.id == lesson_id), None)
    if index is None or index + 1 >= len(lessons):
        return None
    return lessons[index + 1]


class ProgressionService:
    def __init__(
        self,
        session: AsyncSession,
        curriculum: CurriculumService,
        freelancer: FreelancerService,
        gamification: GamificationService,
        tours: TourService,
        ai: AiService,
        analytics: Analytics,
    ) -> None:
        self._session = session
        self._curriculum = curriculum
        self._freelancer = freelancer
        self._gamification = gamification
        self._tours = tours
        self._ai = ai
        self._analytics = analytics

    # ---------- shared lookups ----------

    async def _context(self, user: CurrentUser) -> tuple[FreelancerProfile, LearningPath]:
        profile = await self._freelancer.get_profile(user.id)
        if profile is None:
            raise AppError("onboarding_required", "Finish the short quiz to set up your journey.", 409)
        return profile, await self._curriculum.get_path_by_id(profile.learning_path_id)

    async def _progress(self, user: CurrentUser) -> dict[str, str]:
        rows = await self._session.execute(
            select(LessonProgress.lesson_id, LessonProgress.status).where(LessonProgress.user_id == user.id)
        )
        return {row.lesson_id: row.status for row in rows}

    @staticmethod
    def _first_fact(path: LearningPath, progress: dict[str, str]) -> FirstLessonFact:
        return progress.get(path.first_lesson_id, "not_started")  # type: ignore[return-value]

    async def _states(self, user: CurrentUser, lesson_id: str) -> dict[str, ActionState]:
        """Newest attempt per action. A completed action stays completed even if a later attempt fails."""
        rows = await self._session.scalars(
            select(ActionAttempt)
            .where(ActionAttempt.user_id == user.id, ActionAttempt.lesson_id == lesson_id)
            .order_by(ActionAttempt.created_at, ActionAttempt.id)
        )
        states: dict[str, ActionState] = {}
        for attempt in rows:
            previous = states.get(attempt.action_key)
            if previous and previous.completed and not attempt.completed:
                # e.g. a failed quiz retake after passing: keep the pass, show the newest result.
                states[attempt.action_key] = ActionState(
                    completed=True,
                    payload=attempt.payload,
                    result=attempt.result,
                    updated_at=attempt.created_at,
                )
            else:
                states[attempt.action_key] = ActionState(
                    completed=attempt.completed,
                    payload=attempt.payload,
                    result=attempt.result,
                    updated_at=attempt.created_at,
                )
        return states

    def _accessible_lesson(self, path: LearningPath, progress: dict[str, str], lesson_id: str) -> Lesson:
        lesson = path.lesson(lesson_id)
        if lesson is None:
            raise not_found("Lesson")
        status = engine.lesson_statuses([item.id for item in path.lessons], progress)[lesson.id]
        if status == "locked":
            raise AppError("lesson_locked", "Finish the current lesson to unlock this one.", 403)
        if not lesson.playable:
            raise AppError("lesson_unavailable", "This lesson is not available yet.", 409)
        return lesson

    async def _achievements_out(self, user: CurrentUser, path: LearningPath) -> list[AchievementOut]:
        earned = await self._gamification.earned(user.id)
        return [
            AchievementOut(
                key=a.key,
                title=a.title,
                description=a.description,
                earned=a.key in earned,
                earned_at=earned.get(a.key),
            )
            for a in path.achievements
        ]

    @staticmethod
    def _new_achievements_out(achievements: list[Achievement]) -> list[AchievementOut]:
        return [
            AchievementOut(
                key=a.key, title=a.title, description=a.description, earned=True, earned_at=utcnow()
            )
            for a in achievements
        ]

    # ---------- journey ----------

    async def journey(self, user: CurrentUser) -> JourneyOut:
        profile, path = await self._context(user)
        progress = await self._progress(user)
        statuses = engine.lesson_statuses([lesson.id for lesson in path.lessons], progress)
        tour = await self._tours.get_or_start(user.id, self._first_fact(path, progress))

        chapters = [
            ChapterOut(
                id=chapter.id,
                theme=chapter.theme,
                tier=chapter.tier,
                title=chapter.title,
                blurb=chapter.blurb,
                lessons=[
                    LessonNodeOut(
                        id=lesson.id,
                        title=lesson.title,
                        minutes=lesson.minutes,
                        xp=lesson.xp,
                        summary=lesson.summary,
                        parts=[PartOut(**part.model_dump()) for part in lesson.parts],
                        output=lesson.output,
                        status=statuses[lesson.id],
                        reward_pending=progress.get(lesson.id) == "reward_pending",
                        started=progress.get(lesson.id) == "in_progress",
                        playable=lesson.playable,
                    )
                    for lesson in chapter.lessons
                ],
            )
            for chapter in path.chapters
        ]
        current = next((lesson.id for lesson in path.lessons if statuses[lesson.id] == "current"), None)
        pending = next((lid for lid, status in progress.items() if status == "reward_pending"), None)

        last_reward: RewardOut | None = None
        if tour.status == "active" and tour.stage == "first_reward_claimed":
            last_reward = await self._reward_from_ledger(user, path, path.lesson(path.first_lesson_id))

        xp_total = await self._gamification.total_xp(user.id)
        out = JourneyOut(
            path_id=path.id,
            path_title=path.title,
            track_label=f"{quiz.label('domain', profile.domain)} · "
            f"{quiz.label('specialization', profile.specialization)}",
            welcome=f"Your path from {quiz.ROLE.get(profile.specialization, 'software developer')} "
            "to independent freelancer",
            chapters=chapters,
            first_lesson_id=path.first_lesson_id,
            current_lesson_id=current,
            pending_reward_lesson_id=pending,
            last_reward=last_reward,
            xp_total=xp_total,
            rank=rank_out(xp_total),
            streak=streak_out(*await self._gamification.streak(user.id, self._today(profile))),
            completed_count=sum(1 for status in statuses.values() if status == "done"),
            total_count=len(statuses),
            profile=profile_out(profile),
            tour=_tour_out(tour),
            achievements=await self._achievements_out(user, path),
            avatars=list(path.avatars),
            more_coming=path.more_coming,
        )
        await self._session.commit()  # the tour row may have been created or reconciled
        return out

    @staticmethod
    def _today(profile: FreelancerProfile):
        return local_day(utcnow(), profile.timezone)

    async def profile_page(self, user: CurrentUser) -> ProfilePageOut:
        profile, path = await self._context(user)
        progress = await self._progress(user)
        xp_total = await self._gamification.total_xp(user.id)
        return ProfilePageOut(
            email=user.email,
            profile=profile_out(profile),
            xp_total=xp_total,
            rank=rank_out(xp_total),
            ranks=rank_ladder(xp_total),
            streak=streak_out(*await self._gamification.streak(user.id, self._today(profile))),
            achievements=await self._achievements_out(user, path),
            assets=[asset_out(a) for a in await self._freelancer.list_assets(user.id)],
            completed_count=sum(1 for status in progress.values() if status == "completed"),
            total_count=len(path.lessons),
            avatars=list(path.avatars),
        )

    async def set_timezone(self, user: CurrentUser, timezone: str) -> None:
        if not valid_timezone(timezone):
            raise AppError("invalid_timezone", "Unknown time zone.", 422)
        profile, _ = await self._context(user)
        if profile.timezone != timezone:
            profile.timezone = timezone
            await self._session.commit()

    async def _reward_from_ledger(
        self, user: CurrentUser, path: LearningPath, lesson: Lesson | None
    ) -> RewardOut | None:
        """Rebuild an already-paid reward from stored facts (used to re-show the celebration)."""
        if lesson is None:
            return None
        amount = await self._session.scalar(
            select(XpEvent.amount).where(
                XpEvent.user_id == user.id, XpEvent.idempotency_key == xp_key(lesson.id)
            )
        )
        if amount is None:
            return None
        xp_total = await self._gamification.total_xp(user.id)
        return RewardOut(
            lesson_id=lesson.id,
            lesson_title=lesson.title,
            xp_awarded=amount,
            xp_total=xp_total,
            achievements=[a for a in await self._achievements_out(user, path) if a.earned],
            next_lesson=_lesson_ref(_next_lesson(path, lesson.id)),
            rank=rank_out(xp_total),
            rank_up=rank_for(xp_total).number > rank_for(xp_total - amount).number,
        )

    # ---------- lesson ----------

    async def lesson(self, user: CurrentUser, lesson_id: str) -> LessonOut:
        profile, path = await self._context(user)
        progress = await self._progress(user)
        lesson = self._accessible_lesson(path, progress, lesson_id)
        states = await self._states(user, lesson.id)
        tour = await self._tours.get_or_start(user.id, self._first_fact(path, progress))
        out = self._lesson_out(path, lesson, progress, states, profile, tour)
        await self._session.commit()
        return out

    def _lesson_out(
        self,
        path: LearningPath,
        lesson: Lesson,
        progress: dict[str, str],
        states: dict[str, ActionState],
        profile: FreelancerProfile,
        tour: TourProgress,
    ) -> LessonOut:
        assert lesson.content is not None
        chapter_index, chapter = next(
            (i, c) for i, c in enumerate(path.chapters) if any(item.id == lesson.id for item in c.lessons)
        )
        missing = engine.missing_required_actions(lesson, states)
        progress_status = progress.get(lesson.id, "not_started")
        return LessonOut(
            id=lesson.id,
            title=lesson.title,
            minutes=lesson.minutes,
            xp=lesson.xp,
            summary=lesson.summary,
            output=lesson.output,
            parts=[PartOut(**part.model_dump()) for part in lesson.parts],
            chapter=LessonChapterOut(
                id=chapter.id,
                title=chapter.title,
                theme=chapter.theme,
                index=chapter_index,
                lesson_index=next(i for i, item in enumerate(chapter.lessons) if item.id == lesson.id),
                lesson_count=len(chapter.lessons),
            ),
            is_first_lesson=lesson.id == path.first_lesson_id,
            status="done" if progress_status == "completed" else "current",
            progress_status=progress_status,  # type: ignore[arg-type]
            blocks=[block_view(block, profile) for block in lesson.content.blocks],
            actions=[action_view(lesson, action, states, profile) for action in lesson.content.actions],
            completable=not missing and progress_status in ("not_started", "in_progress"),
            missing_required=missing,
            ai_available=self._ai.available,
            content_version=lesson.version,
            next_lesson=_lesson_ref(_next_lesson(path, lesson.id)),
            tour=_tour_out(tour),
        )

    async def _ensure_progress(self, user: CurrentUser, path: LearningPath, lesson: Lesson) -> bool:
        """Create the progress row if needed. Returns True when this call created it."""
        inserted = (
            await self._session.execute(
                insert(LessonProgress)
                .values(
                    user_id=user.id,
                    path_id=path.id,
                    lesson_id=lesson.id,
                    status="in_progress",
                    content_version=lesson.version,
                )
                .on_conflict_do_nothing(index_elements=[LessonProgress.user_id, LessonProgress.lesson_id])
                .returning(LessonProgress.id)
            )
        ).first()
        if inserted is not None:
            await self._session.execute(
                insert(LessonSnapshot)
                .values(lesson_id=lesson.id, version=lesson.version, payload=lesson.model_dump(mode="json"))
                .on_conflict_do_nothing()
            )
        return inserted is not None

    async def start_lesson(self, user: CurrentUser, lesson_id: str) -> LessonOut:
        """Idempotent. Records that the learner opened the lesson."""
        profile, path = await self._context(user)
        progress = await self._progress(user)
        lesson = self._accessible_lesson(path, progress, lesson_id)
        created = await self._ensure_progress(user, path, lesson)
        if created:
            progress[lesson.id] = "in_progress"
        is_first = lesson.id == path.first_lesson_id
        fact = self._first_fact(path, progress)
        if is_first:
            tour = await self._tours.apply(user.id, "first_lesson_opened", fact)
        else:
            tour = await self._tours.get_or_start(user.id, fact)
        states = await self._states(user, lesson.id)
        out = self._lesson_out(path, lesson, progress, states, profile, tour)
        await self._session.commit()
        if created:
            self._analytics.capture(
                str(user.id),
                "first_lesson_started" if is_first else "lesson_started",
                {"lesson_id": lesson.id},
            )
        return out

    # ---------- actions ----------

    async def submit_action(
        self, user: CurrentUser, lesson_id: str, action_key: str, payload: dict[str, Any]
    ) -> ActionSubmitOut:
        profile, path = await self._context(user)
        progress = await self._progress(user)
        lesson = self._accessible_lesson(path, progress, lesson_id)
        action = lesson.action(action_key)
        if action is None:
            raise not_found("Action")
        states = await self._states(user, lesson.id)
        unmet = engine.unmet_dependencies(lesson, action.key, states)
        if unmet:
            raise AppError("dependency_not_met", "Finish the earlier step first.", 409, {"requires": unmet})

        outcome = await HANDLERS[action.type](
            ActionContext(
                user_id=user.id,
                lesson=lesson,
                action=action,
                payload=payload,
                states=states,
                freelancer=self._freelancer,
                ai=self._ai,
            )
        )

        await self._ensure_progress(user, path, lesson)
        self._session.add(
            ActionAttempt(
                user_id=user.id,
                lesson_id=lesson.id,
                action_key=action.key,
                action_type=action.type,
                payload=outcome.payload,
                result=outcome.result,
                completed=outcome.completed,
                content_version=lesson.version,
            )
        )
        await self._session.flush()
        if outcome.completed:
            await self._gamification.record_activity(user.id, self._today(profile))
        new_achievements: list[Achievement] = []
        if outcome.asset_created:
            new_achievements = await self._gamification.evaluate_achievements(user.id, path)
        states = await self._states(user, lesson.id)
        missing = engine.missing_required_actions(lesson, states)
        out = ActionSubmitOut(
            action=action_view(lesson, action, states, profile),
            actions=[action_view(lesson, item, states, profile) for item in lesson.content.actions],  # type: ignore[union-attr]
            completable=not missing and progress.get(lesson.id, "in_progress") == "in_progress",
            missing_required=missing,
            achievements=self._new_achievements_out(new_achievements),
        )
        await self._session.commit()

        self._analytics.capture(
            str(user.id),
            "action_submitted",
            {
                "lesson_id": lesson.id,
                "action_key": action.key,
                "action_type": action.type,
                "completed": outcome.completed,
            },
        )
        if outcome.asset_created:
            self._analytics.capture(
                str(user.id),
                "freelancer_asset_created",
                {"asset_type": outcome.result.get("asset_type"), "lesson_id": lesson.id},
            )
        return out

    # ---------- completion and rewards ----------

    async def complete_lesson(self, user: CurrentUser, lesson_id: str) -> CompleteOut:
        profile, path = await self._context(user)
        progress = await self._progress(user)
        lesson = self._accessible_lesson(path, progress, lesson_id)

        is_first = lesson.id == path.first_lesson_id
        if is_first:
            # Same lock order as select_avatar (profile, then progress), so the "has an avatar?" check
            # below cannot race with an avatar being saved.
            profile = await self._session.scalar(
                select(FreelancerProfile).where(FreelancerProfile.user_id == user.id).with_for_update()
            )
            assert profile is not None
        # Row lock: concurrent completes for the same lesson run one after the other.
        row = await self._session.scalar(
            select(LessonProgress)
            .where(LessonProgress.user_id == user.id, LessonProgress.lesson_id == lesson.id)
            .with_for_update()
        )
        if row is None:
            raise AppError("lesson_not_started", "Open the lesson and finish its steps first.", 409)
        fact = self._first_fact(path, {**progress, lesson.id: row.status})

        if row.status == "completed":
            tour = await self._tours.get_or_start(user.id, fact)
            reward = await self._reward_from_ledger(user, path, lesson)
            await self._session.commit()
            return CompleteOut(
                status="completed", reward=reward, already_completed=True, tour=_tour_out(tour)
            )
        if row.status == "reward_pending":
            tour = await self._tours.get_or_start(user.id, fact)
            await self._session.commit()
            return CompleteOut(
                status="reward_pending", reward=None, already_completed=True, tour=_tour_out(tour)
            )

        missing = engine.missing_required_actions(lesson, await self._states(user, lesson.id))
        if missing:
            raise AppError("lesson_incomplete", "Finish the required steps first.", 409, {"missing": missing})

        row.submitted_at = utcnow()

        if is_first and profile.avatar_key is None:
            # First-run rule: the work is saved now, the reward is paid when the avatar is chosen.
            row.status = "reward_pending"
            tour = await self._tours.apply(user.id, "first_lesson_submitted", "reward_pending")
            await self._session.commit()
            self._analytics.capture(str(user.id), "first_lesson_completed", {"lesson_id": lesson.id})
            return CompleteOut(
                status="reward_pending", reward=None, already_completed=False, tour=_tour_out(tour)
            )

        reward, events = await self._finalize(user, profile, path, lesson, row)
        tour = await self._tours.get_or_start(
            user.id, self._first_fact(path, {**progress, lesson.id: "completed"})
        )
        await self._session.commit()
        self._emit(user, events)
        return CompleteOut(status="completed", reward=reward, already_completed=False, tour=_tour_out(tour))

    async def _finalize(
        self,
        user: CurrentUser,
        profile: FreelancerProfile,
        path: LearningPath,
        lesson: Lesson,
        row: LessonProgress,
    ) -> tuple[RewardOut, list[tuple[str, dict[str, Any]]]]:
        """Mark completed, pay XP once, grant achievements. Caller commits, then emits the events."""
        now = utcnow()
        xp_before = await self._gamification.total_xp(user.id)
        row.status = "completed"
        row.completed_at = now
        row.submitted_at = row.submitted_at or now
        paid = await self._gamification.award_xp(
            user.id, lesson.xp, "lesson_completed", lesson.id, xp_key(lesson.id)
        )
        await self._gamification.record_activity(user.id, self._today(profile))
        await self._session.flush()
        new_achievements = await self._gamification.evaluate_achievements(user.id, path)
        next_lesson = _next_lesson(path, lesson.id)
        xp_total = await self._gamification.total_xp(user.id)
        rank_up = rank_for(xp_total).number > rank_for(xp_before).number
        reward = RewardOut(
            lesson_id=lesson.id,
            lesson_title=lesson.title,
            xp_awarded=lesson.xp if paid else 0,
            xp_total=xp_total,
            achievements=self._new_achievements_out(new_achievements),
            next_lesson=_lesson_ref(next_lesson),
            rank=rank_out(xp_total),
            rank_up=rank_up,
        )
        events: list[tuple[str, dict[str, Any]]] = [("lesson_completed", {"lesson_id": lesson.id})]
        if paid:
            events.append(("xp_awarded", {"lesson_id": lesson.id, "amount": lesson.xp}))
        if next_lesson:
            events.append(("next_lesson_unlocked", {"lesson_id": next_lesson.id}))
        events.extend(("achievement_earned", {"achievement": a.key}) for a in new_achievements)
        if rank_up:
            events.append(("rank_up", {"rank": rank_for(xp_total).number}))
        return reward, events

    def _emit(self, user: CurrentUser, events: list[tuple[str, dict[str, Any]]]) -> None:
        for name, properties in events:
            self._analytics.capture(str(user.id), name, properties)

    async def select_avatar(self, user: CurrentUser, avatar_key: str) -> AvatarOut:
        profile, path = await self._context(user)
        if avatar_key not in path.avatars:
            raise AppError("invalid_avatar", "Choose one of the available characters.", 422)

        # Lock the profile first: every reward-paying path for this user serializes on it.
        locked = await self._session.scalar(
            select(FreelancerProfile).where(FreelancerProfile.user_id == user.id).with_for_update()
        )
        assert locked is not None
        locked.avatar_key = avatar_key

        pending = list(
            await self._session.scalars(
                select(LessonProgress)
                .where(LessonProgress.user_id == user.id, LessonProgress.status == "reward_pending")
                .with_for_update()
            )
        )
        reward: RewardOut | None = None
        events: list[tuple[str, dict[str, Any]]] = [("avatar_selected", {"avatar": avatar_key})]
        for row in pending:
            lesson = path.lesson(row.lesson_id)
            if lesson is None:  # lesson removed by editors: close it without a reward
                row.status = "completed"
                row.completed_at = utcnow()
                continue
            reward, lesson_events = await self._finalize(user, locked, path, lesson, row)
            events.extend(lesson_events)

        progress = await self._progress(user)
        fact = self._first_fact(path, progress)
        if reward is not None:
            tour = await self._tours.apply(user.id, "reward_claimed", fact)
        else:
            tour = await self._tours.get_or_start(user.id, fact)
        await self._session.commit()
        self._emit(user, events)
        return AvatarOut(avatar_key=avatar_key, reward=reward, tour=_tour_out(tour))

    # ---------- tour ----------

    async def tour_event(self, user: CurrentUser, event: str) -> TourOut:
        _, path = await self._context(user)
        progress = await self._progress(user)
        tour = await self._tours.apply(user.id, event, self._first_fact(path, progress))
        await self._session.commit()
        return _tour_out(tour)
