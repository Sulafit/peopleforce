import uuid
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from peopleforce.core.database import Base, Timestamps, UUIDPrimaryKey


class FreelancerProfile(Timestamps, Base):
    """Canonical professional information for one user. One row per user."""

    __tablename__ = "freelancer_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    display_name: Mapped[str | None] = mapped_column(String(120))
    avatar_key: Mapped[str | None] = mapped_column(String(40))
    # IANA name reported by the browser. Decides where a "day" starts for streaks and daily challenges.
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", server_default="UTC")
    learning_path_id: Mapped[str] = mapped_column(String(80))
    domain: Mapped[str] = mapped_column(String(40))
    specialization: Mapped[str] = mapped_column(String(40))
    experience_level: Mapped[str] = mapped_column(String(40))
    freelance_stage: Mapped[str] = mapped_column(String(40))
    existing_assets: Mapped[list[str]] = mapped_column(JSONB, default=list)
    acquisition_channel: Mapped[str] = mapped_column(String(40))
    primary_goal: Mapped[str] = mapped_column(String(40))


class FreelancerAsset(UUIDPrimaryKey, Timestamps, Base):
    """A reusable piece of professional content produced by a learning action."""

    __tablename__ = "freelancer_assets"
    __table_args__ = (
        # One asset per source action; saving again bumps `revision` in place.
        UniqueConstraint("user_id", "asset_type", "source_lesson_id", "source_action_key"),
        CheckConstraint("status IN ('draft', 'approved', 'published')", name="status_valid"),
        CheckConstraint("origin IN ('user', 'ai')", name="origin_valid"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    asset_type: Mapped[str] = mapped_column(String(60))
    source_lesson_id: Mapped[str] = mapped_column(String(80))
    source_action_key: Mapped[str] = mapped_column(String(80))
    content: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # AI output stays `draft` until the user accepts it.
    status: Mapped[str] = mapped_column(String(20), default="approved")
    origin: Mapped[str] = mapped_column(String(10), default="user")
    revision: Mapped[int] = mapped_column(Integer, default=1)
