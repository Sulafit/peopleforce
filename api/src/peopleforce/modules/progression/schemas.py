from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from peopleforce.modules.freelancer.schemas import AssetOut, ProfileOut
from peopleforce.modules.gamification.schemas import RankOut, RankStepOut, StreakOut


class PartOut(BaseModel):
    kind: str
    title: str
    minutes: int


class LessonNodeOut(BaseModel):
    id: str
    title: str
    minutes: int
    xp: int
    summary: str
    parts: list[PartOut]
    output: str
    status: Literal["done", "current", "locked"]
    reward_pending: bool
    # The learner has opened this lesson and not finished it yet.
    started: bool
    playable: bool


class ChapterOut(BaseModel):
    id: str
    theme: str
    tier: str
    title: str
    blurb: str
    lessons: list[LessonNodeOut]


class TourOut(BaseModel):
    stage: str
    status: Literal["active", "skipped", "completed"]


class AchievementOut(BaseModel):
    key: str
    title: str
    description: str
    earned: bool
    earned_at: datetime | None = None


class LessonRef(BaseModel):
    id: str
    title: str
    playable: bool


class RewardOut(BaseModel):
    lesson_id: str
    lesson_title: str
    xp_awarded: int
    xp_total: int
    achievements: list[AchievementOut]
    next_lesson: LessonRef | None
    rank: RankOut
    # True when this reward moved the learner up a rank.
    rank_up: bool = False


class JourneyOut(BaseModel):
    path_id: str
    path_title: str
    track_label: str
    welcome: str
    chapters: list[ChapterOut]
    first_lesson_id: str
    current_lesson_id: str | None
    pending_reward_lesson_id: str | None
    # Set while the first-run tour is at the celebration stage, so a refresh can show it again.
    last_reward: RewardOut | None
    xp_total: int
    rank: RankOut
    streak: StreakOut
    completed_count: int
    total_count: int
    profile: ProfileOut
    tour: TourOut
    achievements: list[AchievementOut]
    avatars: list[str]
    # Shown after the last published level: the path keeps growing.
    more_coming: str | None


class ActionStateOut(BaseModel):
    completed: bool
    payload: dict[str, Any]
    result: dict[str, Any]
    updated_at: datetime | None
    stale: bool


class ActionOut(BaseModel):
    key: str
    type: str
    title: str
    instructions: str | None
    required: bool
    # Type-specific, learner-safe configuration (never includes quiz answers).
    config: dict[str, Any]
    # Keys of actions that must be completed first; empty when the action can run now.
    blocked_by: list[str]
    state: ActionStateOut


class LessonChapterOut(BaseModel):
    id: str
    title: str
    theme: str
    index: int
    lesson_index: int
    lesson_count: int


class LessonOut(BaseModel):
    id: str
    title: str
    minutes: int
    xp: int
    summary: str
    output: str
    parts: list[PartOut]
    chapter: LessonChapterOut
    is_first_lesson: bool
    status: Literal["done", "current"]
    progress_status: Literal["not_started", "in_progress", "reward_pending", "completed"]
    blocks: list[dict[str, Any]]
    actions: list[ActionOut]
    completable: bool
    missing_required: list[str]
    ai_available: bool
    content_version: str
    next_lesson: LessonRef | None
    tour: TourOut


class ActionSubmitIn(BaseModel):
    payload: dict[str, Any] = {}


class ActionSubmitOut(BaseModel):
    action: ActionOut
    # Other actions whose state changed as a side effect (e.g. became unblocked or stale).
    actions: list[ActionOut]
    completable: bool
    missing_required: list[str]
    achievements: list[AchievementOut]


class CompleteOut(BaseModel):
    status: Literal["reward_pending", "completed"]
    # Present when this call (or an earlier one) paid the reward. Null while the avatar step is pending.
    reward: RewardOut | None
    already_completed: bool
    tour: TourOut


class AvatarIn(BaseModel):
    avatar_key: str


class AvatarOut(BaseModel):
    avatar_key: str
    reward: RewardOut | None
    tour: TourOut


class TourEventIn(BaseModel):
    event: Literal["first_lesson_opened", "reward_acknowledged", "next_prompt_acknowledged", "skip", "replay"]


class ProfilePageOut(BaseModel):
    email: str
    profile: ProfileOut
    xp_total: int
    rank: RankOut
    ranks: list[RankStepOut]
    streak: StreakOut
    achievements: list[AchievementOut]
    assets: list[AssetOut]
    completed_count: int
    total_count: int
    avatars: list[str]


class TimezoneIn(BaseModel):
    timezone: str


class DailyChallengeOut(BaseModel):
    key: str
    title: str
    intro: str | None
    xp: int
    action: ActionOut


class DailyOut(BaseModel):
    day: str
    # None when no challenges are published.
    challenge: DailyChallengeOut | None
    completed: bool
    streak: StreakOut


class DailySubmitIn(BaseModel):
    payload: dict[str, Any] = {}


class DailySubmitOut(BaseModel):
    daily: DailyOut
    xp_awarded: int
    xp_total: int
    rank: RankOut
    rank_up: bool
