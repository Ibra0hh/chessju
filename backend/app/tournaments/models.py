import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.time import utc_now
from app.database import Base


class TimeControl(Base):
    __tablename__ = "time_controls"
    __table_args__ = (
        CheckConstraint("base_seconds > 0", name="ck_time_controls_base_seconds_positive"),
        CheckConstraint(
            "increment_seconds >= 0",
            name="ck_time_controls_increment_seconds_non_negative",
        ),
        CheckConstraint("delay_seconds >= 0", name="ck_time_controls_delay_seconds_non_negative"),
        CheckConstraint(
            "type in ('bullet', 'blitz', 'rapid', 'classical', 'custom')",
            name="ck_time_controls_type_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    base_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    increment_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    tournaments: Mapped[list["Tournament"]] = relationship(back_populates="time_control")


class Tournament(Base):
    __tablename__ = "tournaments"
    __table_args__ = (
        CheckConstraint(
            (
                "status in ('draft', 'published', 'registration_open', "
                "'registration_closed', 'check_in', 'in_progress', 'completed', "
                "'cancelled')"
            ),
            name="ck_tournaments_status_valid",
        ),
        CheckConstraint(
            "format in ('swiss', 'round_robin', 'knockout', 'arena', 'manual')",
            name="ck_tournaments_format_valid",
        ),
        CheckConstraint(
            "max_players is null or max_players > 0",
            name="ck_tournaments_max_players_positive",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft", index=True)
    format: Mapped[str] = mapped_column(Text, nullable=False)
    time_control_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("time_controls.id", ondelete="SET NULL"), nullable=True
    )
    max_players: Mapped[int | None] = mapped_column(Integer, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    registration_open_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    registration_close_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    cover_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("files.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    time_control: Mapped[TimeControl | None] = relationship(back_populates="tournaments")
    registrations: Mapped[list["TournamentRegistration"]] = relationship(
        back_populates="tournament"
    )


class TournamentRegistration(Base):
    __tablename__ = "tournament_registrations"
    __table_args__ = (
        UniqueConstraint("tournament_id", "user_id", name="uq_tournament_registrations_user"),
        CheckConstraint(
            "status in ('pending', 'approved', 'waitlisted', 'cancelled', 'rejected')",
            name="ck_tournament_registrations_status_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tournament_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tournaments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    seed_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tournament: Mapped[Tournament] = relationship(back_populates="registrations")
