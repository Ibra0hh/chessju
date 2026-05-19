import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ArticleStatus = Literal["draft", "published", "archived"]
AnnouncementTarget = Literal["all", "members", "admins", "tournament_players"]
AnnouncementPriority = Literal["normal", "important", "urgent"]
AnnouncementStatus = Literal["draft", "published", "archived"]


class ArticleCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    slug: str | None = Field(default=None, min_length=1, max_length=220)
    summary: str | None = Field(default=None, max_length=500)
    body_markdown: str = Field(min_length=1)
    cover_file_id: uuid.UUID | None = None

    @field_validator("title", "slug", "summary", "body_markdown")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Text fields cannot be blank")
        return normalized or None


class ArticleUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    slug: str | None = Field(default=None, min_length=1, max_length=220)
    summary: str | None = Field(default=None, max_length=500)
    body_markdown: str | None = Field(default=None, min_length=1)
    cover_file_id: uuid.UUID | None = None

    @field_validator("title", "slug", "summary", "body_markdown")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Text fields cannot be blank")
        return normalized or None


class ArticleSummaryResponse(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    summary: str | None
    cover_file_id: uuid.UUID | None
    status: str
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ArticleResponse(ArticleSummaryResponse):
    author_id: uuid.UUID
    body_markdown: str
    deleted_at: datetime | None


class ArticleListResponse(BaseModel):
    items: list[ArticleSummaryResponse]
    limit: int
    offset: int
    total: int


class AdminArticleListResponse(BaseModel):
    items: list[ArticleResponse]
    limit: int
    offset: int
    total: int


class AnnouncementCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    message: str = Field(min_length=1, max_length=2000)
    target: AnnouncementTarget = "all"
    priority: AnnouncementPriority = "normal"
    status: AnnouncementStatus = "published"
    expires_at: datetime | None = None
    tournament_id: uuid.UUID | None = None

    @field_validator("title", "message")
    @classmethod
    def strip_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Text fields cannot be blank")
        return normalized


class AnnouncementUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    message: str | None = Field(default=None, min_length=1, max_length=2000)
    target: AnnouncementTarget | None = None
    priority: AnnouncementPriority | None = None
    expires_at: datetime | None = None
    tournament_id: uuid.UUID | None = None

    @field_validator("title", "message")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Text fields cannot be blank")
        return normalized or None


class AnnouncementResponse(BaseModel):
    id: uuid.UUID
    created_by: uuid.UUID
    title: str
    message: str
    target: str
    priority: str
    status: str
    published_at: datetime | None
    expires_at: datetime | None
    tournament_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class AnnouncementListResponse(BaseModel):
    items: list[AnnouncementResponse]
    limit: int
    offset: int
    total: int


class DeleteResponse(BaseModel):
    deleted: bool


class HomeResponse(BaseModel):
    announcements: list[AnnouncementResponse]
    latest_news: list[ArticleSummaryResponse]
    upcoming_tournaments: list[dict[str, Any]]
    leaderboard_preview: list[dict[str, Any]]
