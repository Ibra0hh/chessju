import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.time import utc_now
from app.database import Base


class ChessComAccount(Base):
    __tablename__ = "chesscom_accounts"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_chesscom_accounts_user_id"),
        UniqueConstraint("username", name="uq_chesscom_accounts_username"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    username: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    profile_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_online_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class ChessComSyncJob(Base):
    __tablename__ = "chesscom_sync_jobs"
    __table_args__ = (
        CheckConstraint(
            "status in ('queued', 'running', 'completed', 'failed', 'cancelled')",
            name="ck_chesscom_sync_jobs_status_valid",
        ),
        CheckConstraint(
            "archive_months_requested is null or archive_months_requested > 0",
            name="ck_chesscom_sync_jobs_months_positive",
        ),
        CheckConstraint("games_found >= 0", name="ck_chesscom_sync_jobs_games_found_nonnegative"),
        CheckConstraint(
            "games_imported >= 0",
            name="ck_chesscom_sync_jobs_games_imported_nonnegative",
        ),
        CheckConstraint(
            "games_skipped >= 0",
            name="ck_chesscom_sync_jobs_games_skipped_nonnegative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chesscom_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chesscom_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued", index=True)
    archive_months_requested: Mapped[int | None] = mapped_column(Integer, nullable=True)
    games_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    games_imported: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    games_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ChessComImportedGame(Base):
    __tablename__ = "chesscom_imported_games"
    __table_args__ = (
        UniqueConstraint("chesscom_url", name="uq_chesscom_imported_games_url"),
        UniqueConstraint("game_id", name="uq_chesscom_imported_games_game_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chesscom_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chesscom_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chesscom_url: Mapped[str] = mapped_column(Text, nullable=False)
    chesscom_uuid: Mapped[str | None] = mapped_column(Text, nullable=True)
    played_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    time_class: Mapped[str | None] = mapped_column(Text, nullable=True)
    time_control: Mapped[str | None] = mapped_column(Text, nullable=True)
    rated: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    white_username: Mapped[str | None] = mapped_column(Text, nullable=True)
    black_username: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
