"""Imports every ORM model so `Base.metadata` is complete (used by Alembic and tests)."""

from peopleforce.core.database import Base
from peopleforce.modules.ai.models import AiGeneration
from peopleforce.modules.auth.models import MagicLinkChallenge, Session, User
from peopleforce.modules.freelancer.models import FreelancerAsset, FreelancerProfile
from peopleforce.modules.gamification.models import ActivityDay, DailyChallengeEntry, UserAchievement, XpEvent
from peopleforce.modules.onboarding.models import OnboardingDraft
from peopleforce.modules.progression.models import ActionAttempt, LessonProgress, LessonSnapshot
from peopleforce.modules.tours.models import TourProgress

__all__ = [
    "ActionAttempt",
    "ActivityDay",
    "AiGeneration",
    "Base",
    "DailyChallengeEntry",
    "FreelancerAsset",
    "FreelancerProfile",
    "LessonProgress",
    "LessonSnapshot",
    "MagicLinkChallenge",
    "OnboardingDraft",
    "Session",
    "TourProgress",
    "User",
    "UserAchievement",
    "XpEvent",
]
