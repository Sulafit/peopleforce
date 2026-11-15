import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from peopleforce.core.database import Base, Timestamps, UUIDPrimaryKey


class OnboardingDraft(UUIDPrimaryKey, Timestamps, Base):
    """Quiz answers given before an account exists. The browser only holds an opaque token for it."""

    __tablename__ = "onboarding_drafts"
    __table_args__ = (
        CheckConstraint("status IN ('in_progress', 'completed', 'claimed')", name="status_valid"),
    )

    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="in_progress")
    # {question_id: value}; validated against the quiz definition on every write.
    answers: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    # PersonalizationProfile, set when the quiz is completed.
    profile: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    claimed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
