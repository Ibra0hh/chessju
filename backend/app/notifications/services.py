import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.services import sanitize_audit_payload
from app.common.time import utc_now
from app.notifications.models import Notification, NotificationPreference
from app.notifications.schemas import (
    MarkAllReadResponse,
    NotificationListResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdateRequest,
    NotificationResponse,
    UnreadCountResponse,
)
from app.realtime.services import create_realtime_event

NOTIFICATION_PREFERENCE_FIELD_BY_TYPE = {
    "friend_request.received": "friend_requests",
    "friend_request.accepted": "friend_requests",
    "message.received": "chat_messages",
    "analysis.completed": "analysis_updates",
    "analysis.failed": "analysis_updates",
    "chesscom.sync_completed": "chesscom_sync_updates",
    "chesscom.sync_failed": "chesscom_sync_updates",
    "announcement.published": "news_announcements",
    "news.published": "news_announcements",
    "tournament.registration_confirmed": "tournament_updates",
    "tournament.registration_waitlisted": "tournament_updates",
    "tournament.updated": "tournament_updates",
    "pairing.published": "tournament_updates",
    "result.submitted": "tournament_updates",
    "leaderboard.updated": "tournament_updates",
}


async def get_or_create_notification_preferences(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> NotificationPreference:
    preferences = await session.get(NotificationPreference, user_id)
    if preferences is not None:
        return preferences
    preferences = NotificationPreference(user_id=user_id)
    session.add(preferences)
    await session.flush()
    return preferences


def _notification_allowed(preferences: NotificationPreference, notification_type: str) -> bool:
    if not preferences.in_app_enabled:
        return False
    preference_field = NOTIFICATION_PREFERENCE_FIELD_BY_TYPE.get(notification_type)
    if preference_field is None:
        return True
    return bool(getattr(preferences, preference_field))


def _safe_notification_data(data: dict[str, Any] | None) -> dict[str, Any]:
    sanitized = sanitize_audit_payload(data or {})
    normalized = _json_safe(sanitized)
    return normalized if isinstance(normalized, dict) else {}


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


async def create_user_notification(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    notification_type: str,
    title: str,
    body: str | None = None,
    data: dict[str, Any] | None = None,
    channel: str | None = None,
) -> Notification | None:
    preferences = await get_or_create_notification_preferences(session, user_id)
    if not _notification_allowed(preferences, notification_type):
        return None

    safe_data = _safe_notification_data(data)
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        body=body,
        data=safe_data,
    )
    session.add(notification)
    await session.flush()

    event_payload = {
        "notification_id": str(notification.id),
        "type": notification.type,
        "title": notification.title,
        "body": notification.body,
        "data": safe_data,
        "created_at": notification.created_at.isoformat(),
    }
    await create_realtime_event(
        session,
        user_id=user_id,
        channel=channel or f"user:{user_id}",
        event_type=notification_type,
        payload=event_payload,
    )
    return notification


async def create_broadcast_realtime_event(
    session: AsyncSession,
    *,
    channel: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> None:
    await create_realtime_event(
        session,
        channel=channel,
        event_type=event_type,
        payload=_safe_notification_data(payload),
        user_id=None,
    )


def _notification_filters(
    statement: Select[tuple[Notification]],
    user_id: uuid.UUID | None,
    notification_type: str | None,
    unread_only: bool,
) -> Select[tuple[Notification]]:
    if user_id is not None:
        statement = statement.where(Notification.user_id == user_id)
    if notification_type is not None:
        statement = statement.where(Notification.type == notification_type)
    if unread_only:
        statement = statement.where(Notification.read_at.is_(None))
    return statement


async def list_user_notifications(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> NotificationListResponse:
    statement = _notification_filters(select(Notification), user_id, None, unread_only)
    count_statement = _notification_filters(
        select(func.count()).select_from(Notification),
        user_id,
        None,
        unread_only,
    )
    total = await session.scalar(count_statement)
    result = await session.execute(
        statement.order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(item) for item in result.scalars()],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


async def unread_count(session: AsyncSession, user_id: uuid.UUID) -> UnreadCountResponse:
    count = await session.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None))
    )
    return UnreadCountResponse(unread_count=count or 0)


async def mark_notification_read(
    session: AsyncSession,
    user_id: uuid.UUID,
    notification_id: uuid.UUID,
) -> NotificationResponse:
    notification = await session.get(Notification, notification_id)
    if notification is None or notification.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    if notification.read_at is None:
        notification.read_at = utc_now()
        await session.commit()
        await session.refresh(notification)
    return NotificationResponse.model_validate(notification)


async def mark_all_notifications_read(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> MarkAllReadResponse:
    read_at = utc_now()
    result = await session.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        .values(read_at=read_at)
    )
    await session.commit()
    return MarkAllReadResponse(marked_read=result.rowcount or 0, read_at=read_at)


async def get_preferences(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> NotificationPreferenceResponse:
    preferences = await get_or_create_notification_preferences(session, user_id)
    await session.commit()
    await session.refresh(preferences)
    return NotificationPreferenceResponse.model_validate(preferences)


async def update_preferences(
    session: AsyncSession,
    user_id: uuid.UUID,
    payload: NotificationPreferenceUpdateRequest,
) -> NotificationPreferenceResponse:
    preferences = await get_or_create_notification_preferences(session, user_id)
    update_data = payload.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        setattr(preferences, field_name, value)
    preferences.updated_at = utc_now()
    await session.commit()
    await session.refresh(preferences)
    return NotificationPreferenceResponse.model_validate(preferences)


async def list_admin_notifications(
    session: AsyncSession,
    *,
    user_id: uuid.UUID | None = None,
    notification_type: str | None = None,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> NotificationListResponse:
    statement = _notification_filters(select(Notification), user_id, notification_type, unread_only)
    count_statement = _notification_filters(
        select(func.count()).select_from(Notification),
        user_id,
        notification_type,
        unread_only,
    )
    total = await session.scalar(count_statement)
    result = await session.execute(
        statement.order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(item) for item in result.scalars()],
        limit=limit,
        offset=offset,
        total=total or 0,
    )
