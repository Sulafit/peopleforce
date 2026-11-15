"""Anonymous quiz drafts and their one-time attachment to an account.

Draft state machine:  in_progress -> completed -> claimed
  * in_progress/completed: owned by whoever holds the opaque browser token.
  * completed -> in_progress when an answer changes (the profile must be rebuilt).
  * claimed: attached to exactly one user, by an atomic conditional UPDATE. Terminal.
"""

import uuid
from datetime import timedelta
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from peopleforce.core.config import Settings
from peopleforce.core.errors import AppError
from peopleforce.core.security import hash_token, new_token, utcnow
from peopleforce.modules.curriculum.schemas import LearningPath
from peopleforce.modules.freelancer.service import FreelancerService
from peopleforce.modules.onboarding import quiz
from peopleforce.modules.onboarding.models import OnboardingDraft
from peopleforce.modules.onboarding.schemas import PreviewChapter, PreviewOut

log = structlog.get_logger()


class OnboardingService:
    def __init__(self, session: AsyncSession, settings: Settings, freelancer: FreelancerService) -> None:
        self._session = session
        self._settings = settings
        self._freelancer = freelancer

    async def find_draft(self, token: str | None) -> OnboardingDraft | None:
        """The live (unclaimed, unexpired) draft for a browser token."""
        if not token:
            return None
        return await self._session.scalar(
            select(OnboardingDraft).where(
                OnboardingDraft.token_hash == hash_token(token),
                OnboardingDraft.status != "claimed",
                OnboardingDraft.expires_at > utcnow(),
            )
        )

    async def save_answer(
        self, token: str | None, question_id: str, value: Any
    ) -> tuple[OnboardingDraft, str | None]:
        """Store one answer. Creates the draft on first use; returns (draft, new_token_or_None)."""
        normalized = quiz.validate_answer(question_id, value)
        draft = await self.find_draft(token)
        issued: str | None = None
        if draft is None:
            issued = new_token()
            draft = OnboardingDraft(
                token_hash=hash_token(issued),
                answers={},
                expires_at=utcnow() + timedelta(days=self._settings.onboarding_draft_ttl_days),
            )
            self._session.add(draft)
        draft.answers = {**draft.answers, question_id: normalized}
        if draft.status == "completed":
            draft.status = "in_progress"
            draft.profile = None
        await self._session.commit()
        return draft, issued

    async def complete(self, token: str | None) -> OnboardingDraft:
        draft = await self.find_draft(token)
        if draft is None:
            raise AppError(
                "draft_not_found", "Your answers were not found. Please start the quiz again.", 404
            )
        profile = quiz.build_profile(draft.answers)
        draft.profile = quiz.dump_profile(profile)
        draft.status = "completed"
        await self._session.commit()
        return draft

    async def require_completed(self, token: str | None) -> OnboardingDraft:
        draft = await self.find_draft(token)
        if draft is None:
            raise AppError(
                "draft_not_found", "Your answers were not found. Please start the quiz again.", 404
            )
        if draft.status != "completed" or not draft.profile:
            raise AppError("quiz_incomplete", "Finish the quiz to see your journey.", 409)
        return draft

    @staticmethod
    def preview(draft: OnboardingDraft, path: LearningPath) -> PreviewOut:
        assert draft.profile is not None
        profile = quiz.load_profile(draft.profile)
        first = path.chapters[0].lessons[0]
        return PreviewOut(
            headline=f"Your path from {quiz.role_label(profile)} to independent freelancer",
            specialization_label=quiz.label("specialization", profile.specialization),
            stage_label=quiz.label("freelance_stage", profile.freelance_stage),
            stage_line=quiz.STAGE_LINE[profile.freelance_stage],
            goal_label=quiz.label("primary_goal", profile.primary_goal),
            channel_label=quiz.label("acquisition_channel", profile.acquisition_channel),
            milestones=quiz.milestones(profile),
            chapters=[
                PreviewChapter(title=c.title, theme=c.theme, blurb=c.blurb, lesson_count=len(c.lessons))
                for c in path.chapters
            ],
            first_lesson_title=first.title,
            first_lesson_minutes=first.minutes,
            total_lessons=len(path.lessons),
        )

    async def claim(self, draft_id: uuid.UUID, user_id: uuid.UUID, path_id: str) -> bool:
        """Attach a completed draft to a user, exactly once. No commit: runs inside the caller's transaction.

        The conditional UPDATE is the lock: of any number of concurrent claims, one matches the row.
        """
        row = (
            await self._session.execute(
                update(OnboardingDraft)
                .where(
                    OnboardingDraft.id == draft_id,
                    OnboardingDraft.status == "completed",
                    OnboardingDraft.claimed_by_user_id.is_(None),
                    OnboardingDraft.expires_at > utcnow(),
                )
                .values(status="claimed", claimed_by_user_id=user_id, claimed_at=utcnow())
                .returning(OnboardingDraft.profile)
            )
        ).first()
        if row is None or not row.profile:
            log.info("onboarding_draft_not_claimable", draft_id=str(draft_id), user_id=str(user_id))
            return False
        await self._freelancer.upsert_from_personalization(user_id, quiz.load_profile(row.profile), path_id)
        return True

    async def claim_and_commit(self, draft_id: uuid.UUID, user_id: uuid.UUID, path_id: str) -> bool:
        claimed = await self.claim(draft_id, user_id, path_id)
        await self._session.commit()
        return claimed
