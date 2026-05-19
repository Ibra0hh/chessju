import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.time import utc_now
from app.realtime.models import RealtimeEvent
from app.realtime.schemas import RealtimeEventListResponse, RealtimeEventResponse


async def create_realtime_event(
    session: AsyncSession,
    *,
    channel: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
    user_id: uuid.UUID | None = None,
) -> RealtimeEvent:
    event = RealtimeEvent(
        user_id=user_id,
        channel=channel,
        type=event_type,
        payload=payload or {},
    )
    session.add(event)
    await session.flush()
    return event


def _admin_realtime_filters(
    statement: Select[tuple[RealtimeEvent]],
    user_id: uuid.UUID | None,
    channel: str | None,
    event_type: str | None,
) -> Select[tuple[RealtimeEvent]]:
    if user_id is not None:
        statement = statement.where(RealtimeEvent.user_id == user_id)
    if channel is not None:
        statement = statement.where(RealtimeEvent.channel == channel)
    if event_type is not None:
        statement = statement.where(RealtimeEvent.type == event_type)
    return statement


async def list_admin_realtime_events(
    session: AsyncSession,
    *,
    user_id: uuid.UUID | None = None,
    channel: str | None = None,
    event_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> RealtimeEventListResponse:
    statement = _admin_realtime_filters(select(RealtimeEvent), user_id, channel, event_type)
    count_statement = _admin_realtime_filters(
        select(func.count()).select_from(RealtimeEvent),
        user_id,
        channel,
        event_type,
    )
    total = await session.scalar(count_statement)
    result = await session.execute(
        statement.order_by(RealtimeEvent.created_at.desc(), RealtimeEvent.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return RealtimeEventListResponse(
        items=[RealtimeEventResponse.model_validate(event) for event in result.scalars()],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


async def list_stream_events_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    after_created_at: datetime,
    limit: int = 50,
) -> list[RealtimeEvent]:
    result = await session.execute(
        select(RealtimeEvent)
        .where(
            RealtimeEvent.user_id == user_id,
            RealtimeEvent.created_at > after_created_at,
        )
        .order_by(RealtimeEvent.created_at.asc(), RealtimeEvent.id.asc())
        .limit(limit)
    )
    return list(result.scalars())


async def mark_realtime_events_delivered(
    session: AsyncSession,
    events: list[RealtimeEvent],
) -> None:
    now = utc_now()
    for event in events:
        if event.delivered_at is None:
            event.delivered_at = now
    if events:
        await session.commit()
