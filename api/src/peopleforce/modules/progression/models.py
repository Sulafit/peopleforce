import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from peopleforce.core.database import Base, UUIDPrimaryKey


class LessonProgress(UUIDPrimaryKey, Base):
    """One row per user and lesson.

    in_progress -> reward_pending -> completed   (first lesson: the reward waits for an avatar)
    in_progress -> completed                     (every other lesson)
    """

    __tablename__ = "lesson_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id"),
        CheckConstraint("status IN ('in_progress', 'reward_pending', 'completed')", name="status_valid"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    path_id: Mapped[str] = mapped_column(String(80))
    lesson_id: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default="in_progress")
    # Version of the lesson content the learner worked against (see lesson_snapshots).
    content_version: Mapped[str] = mapped_column(String(40))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ActionAttempt(UUIDPrimaryKey, Base):
    """Every accepted action submission. The newest row per (user, lesson, action) is the current state."""

    __tablename__ = "action_attempts"
    __table_args__ = (Index("ix_action_attempts_lookup", "user_id", "lesson_id", "action_key", "created_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    lesson_id: Mapped[str] = mapped_column(String(80))
    action_key: Mapped[str] = mapped_column(String(80))
    action_type: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    completed: Mapped[bool] = mapped_column(default=False)
    content_version: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LessonSnapshot(Base):
    """Immutable copy of a published lesson, keyed by content hash, so old submissions stay readable."""

    __tablename__ = "lesson_snapshots"

    lesson_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    version: Mapped[str] = mapped_column(String(40), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
