import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.time import utc_now
from app.database import Base


class ClockSession(Base):
    __tablename__ = "clock_sessions"
    __table_args__ = (
        CheckConstraint("base_seconds > 0", name="ck_clock_sessions_base_seconds_positive"),
        CheckConstraint(
            "increment_seconds >= 0",
            name="ck_clock_sessions_increment_seconds_non_negative",
        ),
        CheckConstraint("delay_seconds >= 0", name="ck_clock_sessions_delay_seconds_non_negative"),
        CheckConstraint(
            "white_remaining_ms >= 0",
            name="ck_clock_sessions_white_remaining_non_negative",
        ),
        CheckConstraint(
            "black_remaining_ms >= 0",
            name="ck_clock_sessions_black_remaining_non_negative",
        ),
        CheckConstraint(
            "active_color in ('white', 'black', 'none')",
            name="ck_clock_sessions_active_color_valid",
        ),
        CheckConstraint(
            "status in ('setup', 'running', 'paused', 'completed', 'cancelled')",
            name="ck_clock_sessions_status_valid",
        ),
        CheckConstraint(
            (
                "result is null or result in ('white_flagged', 'black_flagged', "
                "'white_win', 'black_win', 'draw', 'aborted', 'manual')"
            ),
            name="ck_clock_sessions_result_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tournament_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tournaments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    pairing_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pairings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    white_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    black_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    base_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    increment_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    white_remaining_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    black_remaining_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    active_color: Mapped[str] = mapped_column(Text, nullable=False, default="none")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="setup", index=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    last_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class ClockEvent(Base):
    __tablename__ = "clock_events"
    __table_args__ = (
        CheckConstraint(
            (
                "event_type in ('setup', 'start', 'pause', 'resume', 'switch_turn', "
                "'adjust_time', 'flag', 'reset', 'complete', 'cancel')"
            ),
            name="ck_clock_events_event_type_valid",
        ),
        CheckConstraint(
            "white_remaining_ms >= 0",
            name="ck_clock_events_white_remaining_non_negative",
        ),
        CheckConstraint(
            "black_remaining_ms >= 0",
            name="ck_clock_events_black_remaining_non_negative",
        ),
        CheckConstraint(
            "active_color in ('white', 'black', 'none')",
            name="ck_clock_events_active_color_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    clock_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clock_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    white_remaining_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    black_remaining_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    active_color: Mapped[str] = mapped_column(Text, nullable=False)
    client_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    server_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    event_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
