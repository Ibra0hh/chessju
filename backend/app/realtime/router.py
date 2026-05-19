import asyncio
import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin
from app.common.time import utc_now
from app.database import AsyncSessionLocal, get_db_session
from app.realtime.models import RealtimeEvent
from app.realtime.schemas import RealtimeEventListResponse
from app.realtime.services import (
    list_admin_realtime_events,
    list_stream_events_for_user,
    mark_realtime_events_delivered,
)
from app.users.models import User

router = APIRouter(tags=["realtime"])


def _event_data(event: RealtimeEvent) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "type": event.type,
        "channel": event.channel,
        "payload": event.payload,
        "created_at": event.created_at.isoformat(),
    }


def _format_sse(event: RealtimeEvent) -> str:
    data = json.dumps(_event_data(event), separators=(",", ":"))
    return f"id: {event.id}\nevent: notification\ndata: {data}\n\n"


async def _initial_stream_time(
    last_event_id: str | None,
    user_id: uuid.UUID,
) -> datetime:
    if not last_event_id:
        return utc_now()
    try:
        event_id = uuid.UUID(last_event_id)
    except ValueError:
        return utc_now()
    async with AsyncSessionLocal() as session:
        event = await session.get(RealtimeEvent, event_id)
        if event is None or event.user_id != user_id:
            return utc_now()
        return event.created_at


async def _stream_user_events(user_id: uuid.UUID, last_event_id: str | None):
    after_created_at = await _initial_stream_time(last_event_id, user_id)
    heartbeat_after_seconds = 20
    seconds_since_heartbeat = 0
    while True:
        async with AsyncSessionLocal() as session:
            events = await list_stream_events_for_user(
                session=session,
                user_id=user_id,
                after_created_at=after_created_at,
            )
            if events:
                for event in events:
                    after_created_at = max(after_created_at, event.created_at)
                    yield _format_sse(event)
                await mark_realtime_events_delivered(session, events)
                seconds_since_heartbeat = 0
            else:
                seconds_since_heartbeat += 2
                if seconds_since_heartbeat >= heartbeat_after_seconds:
                    yield ": heartbeat\n\n"
                    seconds_since_heartbeat = 0
        await asyncio.sleep(2)


@router.get("/realtime/stream")
async def realtime_stream(
    current_user: User = Depends(get_current_user),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> StreamingResponse:
    return StreamingResponse(
        _stream_user_events(current_user.id, last_event_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/admin/realtime/events", response_model=RealtimeEventListResponse)
async def admin_realtime_events(
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    user_id: uuid.UUID | None = None,
    channel: str | None = None,
    event_type: str | None = Query(default=None, alias="type"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> RealtimeEventListResponse:
    _ = current_admin
    return await list_admin_realtime_events(
        session=session,
        user_id=user_id,
        channel=channel,
        event_type=event_type,
        limit=limit,
        offset=offset,
    )
