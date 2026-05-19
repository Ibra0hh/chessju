import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.auth.models import UserRole
from app.common.time import utc_now
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    profile: Mapped["Profile"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    preferences: Mapped["UserPreferences"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    user_roles: Mapped[list[UserRole]] = relationship(
        back_populates="user", cascade="all, delete-orphan", foreign_keys=[UserRole.user_id]
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", foreign_keys="RefreshToken.user_id"
    )


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    username: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    university_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    avatar_file_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    chesscom_username: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    user: Mapped[User] = relationship(back_populates="profile")


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    app_theme: Mapped[str] = mapped_column(String(30), nullable=False, default="system")
    board_theme: Mapped[str] = mapped_column(String(30), nullable=False, default="classic")
    accent_color: Mapped[str] = mapped_column(String(30), nullable=False, default="blue")
    clock_sound_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    notification_settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    privacy_settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    user: Mapped[User] = relationship(back_populates="preferences")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    replaced_by_token_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("refresh_tokens.id", ondelete="SET NULL"), nullable=True
    )
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user: Mapped[User] = relationship(back_populates="refresh_tokens", foreign_keys=[user_id])
