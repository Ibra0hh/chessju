import re
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]{3,40}$")


class ProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    username: str
    full_name: str
    university_id: str | None
    avatar_file_id: uuid.UUID | None
    bio: str | None
    chesscom_username: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PreferencesResponse(BaseModel):
    user_id: uuid.UUID
    app_theme: str
    board_theme: str
    accent_color: str
    clock_sound_enabled: bool
    language: str
    notification_settings: dict[str, Any]
    privacy_settings: dict[str, Any]
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CurrentUserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    status: str
    email_verified_at: datetime | None
    created_at: datetime
    roles: list[str]
    profile: ProfileResponse
    preferences: PreferencesResponse


class ProfileUpdateRequest(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=40)
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    university_id: str | None = Field(default=None, max_length=50)
    bio: str | None = Field(default=None, max_length=1000)
    chesscom_username: str | None = Field(default=None, max_length=80)

    @field_validator("username")
    @classmethod
    def validate_username(cls, username: str | None) -> str | None:
        if username is None:
            return None
        normalized = username.strip()
        if not USERNAME_PATTERN.fullmatch(normalized):
            raise ValueError(
                "Username must be 3-40 characters and use letters, numbers, or underscores"
            )
        return normalized

    @field_validator("full_name", "university_id", "bio", "chesscom_username")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class PreferencesUpdateRequest(BaseModel):
    app_theme: str | None = Field(default=None, min_length=1, max_length=30)
    board_theme: str | None = Field(default=None, min_length=1, max_length=30)
    accent_color: str | None = Field(default=None, min_length=1, max_length=30)
    clock_sound_enabled: bool | None = None
    language: str | None = Field(default=None, min_length=2, max_length=10)
    notification_settings: dict[str, Any] | None = None
    privacy_settings: dict[str, Any] | None = None

    @field_validator("app_theme", "board_theme", "accent_color", "language")
    @classmethod
    def strip_optional_preference(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None
