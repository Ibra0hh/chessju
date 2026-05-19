import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    type: str
    title: str
    body: str | None
    data: dict[str, Any]
    read_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    limit: int
    offset: int
    total: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class MarkAllReadResponse(BaseModel):
    marked_read: int
    read_at: datetime


class NotificationPreferenceResponse(BaseModel):
    user_id: uuid.UUID
    in_app_enabled: bool
    tournament_updates: bool
    friend_requests: bool
    chat_messages: bool
    analysis_updates: bool
    chesscom_sync_updates: bool
    news_announcements: bool
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferenceUpdateRequest(BaseModel):
    in_app_enabled: bool | None = None
    tournament_updates: bool | None = None
    friend_requests: bool | None = None
    chat_messages: bool | None = None
    analysis_updates: bool | None = None
    chesscom_sync_updates: bool | None = None
    news_announcements: bool | None = None
