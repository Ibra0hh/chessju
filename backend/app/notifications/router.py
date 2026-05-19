import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin
from app.database import get_db_session
from app.notifications.schemas import (
    MarkAllReadResponse,
    NotificationListResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdateRequest,
    NotificationResponse,
    UnreadCountResponse,
)
from app.notifications.services import (
    get_preferences,
    list_admin_notifications,
    list_user_notifications,
    mark_all_notifications_read,
    mark_notification_read,
    unread_count,
    update_preferences,
)
from app.users.models import User

router = APIRouter(tags=["Notifications"])


@router.get("/notifications", response_model=NotificationListResponse)
async def my_notifications(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> NotificationListResponse:
    return await list_user_notifications(
        session=session,
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )


@router.get("/notifications/unread-count", response_model=UnreadCountResponse)
async def my_unread_count(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> UnreadCountResponse:
    return await unread_count(session=session, user_id=current_user.id)


@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
async def read_notification(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> NotificationResponse:
    return await mark_notification_read(
        session=session,
        user_id=current_user.id,
        notification_id=notification_id,
    )


@router.post("/notifications/read-all", response_model=MarkAllReadResponse)
async def read_all_notifications(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> MarkAllReadResponse:
    return await mark_all_notifications_read(session=session, user_id=current_user.id)


@router.get("/notifications/preferences", response_model=NotificationPreferenceResponse)
async def my_notification_preferences(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> NotificationPreferenceResponse:
    return await get_preferences(session=session, user_id=current_user.id)


@router.patch("/notifications/preferences", response_model=NotificationPreferenceResponse)
async def update_my_notification_preferences(
    payload: NotificationPreferenceUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> NotificationPreferenceResponse:
    return await update_preferences(session=session, user_id=current_user.id, payload=payload)


@router.get("/admin/notifications", response_model=NotificationListResponse)
async def admin_notifications(
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    user_id: uuid.UUID | None = None,
    notification_type: str | None = Query(default=None, alias="type"),
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> NotificationListResponse:
    _ = current_admin
    return await list_admin_notifications(
        session=session,
        user_id=user_id,
        notification_type=notification_type,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )
