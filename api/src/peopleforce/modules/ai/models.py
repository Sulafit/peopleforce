import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from peopleforce.core.database import Base, UUIDPrimaryKey


class AiGeneration(UUIDPrimaryKey, Base):
    """Audit row for every AI call, successful or not. Also the source for per-user usage limits."""

    __tablename__ = "ai_generations"
    __table_args__ = (Index("ix_ai_generations_user_id_created_at", "user_id", "created_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    capability: Mapped[str] = mapped_column(String(80))
    prompt_name: Mapped[str] = mapped_column(String(120))
    prompt_version: Mapped[str] = mapped_column(String(60))
    model: Mapped[str] = mapped_column(String(80))
    lesson_id: Mapped[str | None] = mapped_column(String(80))
    action_key: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20))  # succeeded | failed
    input: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    # Langfuse trace of this call (when tracing is on), to jump from an audit row to the full trace.
    trace_id: Mapped[str | None] = mapped_column(String(64))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
