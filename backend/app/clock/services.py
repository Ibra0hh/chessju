import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.constants import ADMIN_ROLE_NAMES
from app.clock.models import ClockEvent, ClockSession
from app.clock.schemas import (
    ClockAdjustRequest,
    ClockCancelRequest,
    ClockCompleteRequest,
    ClockEventListResponse,
    ClockEventResponse,
    ClockFlagRequest,
    ClockResetRequest,
    ClockResumeRequest,
    ClockSessionCreateRequest,
    ClockSessionListResponse,
    ClockSessionResponse,
    ClockSnapshotRequest,
    ClockStartRequest,
    ClockSwitchTurnRequest,
)
from app.common.time import utc_now
from app.tournaments.models import Pairing, Tournament
from app.users.models import User
from app.users.services import get_role_names_for_user

ACTIVE_CLOCK_STATUSES = {"setup", "running", "paused"}
MUTATION_TERMINAL_STATUSES = {"completed", "cancelled"}


async def is_admin_user(session: AsyncSession, user: User) -> bool:
    roles = set(await get_role_names_for_user(session, user.id))
    return bool(roles.intersection(ADMIN_ROLE_NAMES))


def _is_official_session(clock_session: ClockSession) -> bool:
    return clock_session.pairing_id is not None or clock_session.tournament_id is not None


async def _get_pairing(session: AsyncSession, pairing_id: uuid.UUID) -> Pairing:
    pairing = await session.get(Pairing, pairing_id)
    if pairing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pairing not found")
    return pairing


async def _get_tournament(session: AsyncSession, tournament_id: uuid.UUID) -> Tournament:
    tournament = await session.get(Tournament, tournament_id)
    if tournament is None or tournament.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")
    return tournament


async def _has_active_pairing_clock(session: AsyncSession, pairing_id: uuid.UUID) -> bool:
    result = await session.execute(
        select(ClockSession.id).where(
            ClockSession.pairing_id == pairing_id,
            ClockSession.status.in_(ACTIVE_CLOCK_STATUSES),
        )
    )
    return result.scalar_one_or_none() is not None


async def can_view_clock_session(
    session: AsyncSession,
    user: User,
    clock_session: ClockSession,
) -> bool:
    if await is_admin_user(session, user):
        return True
    if not _is_official_session(clock_session):
        return clock_session.created_by == user.id
    return user.id in {clock_session.white_user_id, clock_session.black_user_id}


async def can_control_clock_session(
    session: AsyncSession,
    user: User,
    clock_session: ClockSession,
) -> bool:
    if await is_admin_user(session, user):
        return True
    if _is_official_session(clock_session):
        return False
    return clock_session.created_by == user.id


async def get_authorized_clock_session(
    session: AsyncSession,
    user: User,
    clock_session_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> ClockSession:
    statement = select(ClockSession).where(ClockSession.id == clock_session_id)
    if for_update:
        statement = statement.with_for_update()
    result = await session.execute(statement)
    clock_session = result.scalar_one_or_none()
    if clock_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clock session not found")
    if not await can_view_clock_session(session, user, clock_session):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clock session not found")
    return clock_session


async def get_controllable_clock_session(
    session: AsyncSession,
    user: User,
    clock_session_id: uuid.UUID,
) -> ClockSession:
    clock_session = await get_authorized_clock_session(
        session=session,
        user=user,
        clock_session_id=clock_session_id,
        for_update=True,
    )
    if not await can_control_clock_session(session, user, clock_session):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return clock_session


def _event_response(event: ClockEvent) -> ClockEventResponse:
    return ClockEventResponse(
        id=event.id,
        clock_session_id=event.clock_session_id,
        event_type=event.event_type,
        actor_user_id=event.actor_user_id,
        white_remaining_ms=event.white_remaining_ms,
        black_remaining_ms=event.black_remaining_ms,
        active_color=event.active_color,
        client_timestamp=event.client_timestamp,
        server_timestamp=event.server_timestamp,
        metadata=event.event_metadata,
    )


async def _record_event(
    session: AsyncSession,
    clock_session: ClockSession,
    event_type: str,
    actor_user_id: uuid.UUID | None,
    client_timestamp,
    metadata: dict[str, Any] | None = None,
) -> ClockEvent:
    server_timestamp = utc_now()
    event = ClockEvent(
        clock_session_id=clock_session.id,
        event_type=event_type,
        actor_user_id=actor_user_id,
        white_remaining_ms=clock_session.white_remaining_ms,
        black_remaining_ms=clock_session.black_remaining_ms,
        active_color=clock_session.active_color,
        client_timestamp=client_timestamp,
        server_timestamp=server_timestamp,
        event_metadata=metadata or {},
    )
    clock_session.last_event_at = server_timestamp
    session.add(event)
    await session.flush()
    return event


def _apply_snapshot(clock_session: ClockSession, payload: ClockSnapshotRequest) -> None:
    clock_session.white_remaining_ms = payload.white_remaining_ms
    clock_session.black_remaining_ms = payload.black_remaining_ms


def _ensure_status(clock_session: ClockSession, allowed: set[str], action: str) -> None:
    if clock_session.status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot {action} clock session from {clock_session.status} state",
        )


def _ensure_not_terminal(clock_session: ClockSession, action: str) -> None:
    if clock_session.status in MUTATION_TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot {action} a terminal clock session",
        )


async def create_clock_session(
    session: AsyncSession,
    user: User,
    payload: ClockSessionCreateRequest,
) -> ClockSessionResponse:
    user_is_admin = await is_admin_user(session, user)
    tournament_id = payload.tournament_id
    white_user_id = payload.white_user_id
    black_user_id = payload.black_user_id

    if payload.pairing_id is not None:
        if not user_is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can create official pairing clock sessions",
            )
        pairing = await _get_pairing(session, payload.pairing_id)
        if await _has_active_pairing_clock(session, pairing.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An active clock session already exists for this pairing",
            )
        tournament_id = pairing.tournament_id
        white_user_id = payload.white_user_id or pairing.white_user_id
        black_user_id = payload.black_user_id or pairing.black_user_id
    elif payload.tournament_id is not None:
        if not user_is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can create official tournament clock sessions",
            )
        await _get_tournament(session, payload.tournament_id)

    remaining_ms = payload.base_seconds * 1000
    clock_session = ClockSession(
        tournament_id=tournament_id,
        pairing_id=payload.pairing_id,
        white_user_id=white_user_id,
        black_user_id=black_user_id,
        base_seconds=payload.base_seconds,
        increment_seconds=payload.increment_seconds,
        delay_seconds=payload.delay_seconds,
        white_remaining_ms=remaining_ms,
        black_remaining_ms=remaining_ms,
        active_color="none",
        status="setup",
        created_by=user.id,
    )
    session.add(clock_session)
    await session.flush()
    await _record_event(
        session=session,
        clock_session=clock_session,
        event_type="setup",
        actor_user_id=user.id,
        client_timestamp=None,
        metadata={"source": "create_session"},
    )
    await session.commit()
    await session.refresh(clock_session)
    return ClockSessionResponse.model_validate(clock_session)


async def get_clock_session(
    session: AsyncSession,
    user: User,
    clock_session_id: uuid.UUID,
) -> ClockSessionResponse:
    clock_session = await get_authorized_clock_session(session, user, clock_session_id)
    return ClockSessionResponse.model_validate(clock_session)


async def list_clock_events(
    session: AsyncSession,
    user: User,
    clock_session_id: uuid.UUID,
    limit: int = 100,
    offset: int = 0,
) -> ClockEventListResponse:
    clock_session = await get_authorized_clock_session(session, user, clock_session_id)
    statement = select(ClockEvent).where(ClockEvent.clock_session_id == clock_session.id)
    total = await session.scalar(select(func.count()).select_from(statement.subquery()))
    result = await session.execute(
        statement.order_by(ClockEvent.server_timestamp.asc(), ClockEvent.id.asc())
        .limit(limit)
        .offset(offset)
    )
    return ClockEventListResponse(
        items=[_event_response(event) for event in result.scalars()],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


async def _mutate_clock_session(
    session: AsyncSession,
    user: User,
    clock_session_id: uuid.UUID,
    event_type: str,
    payload,
    metadata: dict[str, Any] | None = None,
) -> ClockSessionResponse:
    clock_session = await get_controllable_clock_session(session, user, clock_session_id)

    if event_type == "start":
        _ensure_status(clock_session, {"setup", "paused"}, "start")
        _apply_snapshot(clock_session, payload)
        clock_session.status = "running"
        clock_session.active_color = payload.active_color
        if clock_session.started_at is None:
            clock_session.started_at = utc_now()
        clock_session.completed_at = None
        clock_session.result = None
    elif event_type == "pause":
        _ensure_status(clock_session, {"running"}, "pause")
        _apply_snapshot(clock_session, payload)
        clock_session.status = "paused"
    elif event_type == "resume":
        _ensure_status(clock_session, {"paused"}, "resume")
        _apply_snapshot(clock_session, payload)
        if payload.active_color is not None:
            clock_session.active_color = payload.active_color
        if clock_session.active_color == "none":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="active_color is required to resume this session",
            )
        clock_session.status = "running"
    elif event_type == "switch_turn":
        _ensure_status(clock_session, {"running"}, "switch turn")
        _apply_snapshot(clock_session, payload)
        if payload.active_color == clock_session.active_color:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="active_color must switch to the other side",
            )
        clock_session.active_color = payload.active_color
    elif event_type == "adjust_time":
        _ensure_not_terminal(clock_session, "adjust")
        _apply_snapshot(clock_session, payload)
    elif event_type == "flag":
        _ensure_status(clock_session, {"running", "paused"}, "flag")
        _apply_snapshot(clock_session, payload)
        clock_session.status = "completed"
        clock_session.result = (
            "white_flagged" if payload.flagged_color == "white" else "black_flagged"
        )
        clock_session.active_color = "none"
        clock_session.completed_at = utc_now()
    elif event_type == "complete":
        _ensure_not_terminal(clock_session, "complete")
        _apply_snapshot(clock_session, payload)
        clock_session.status = "completed"
        clock_session.result = payload.result
        clock_session.active_color = "none"
        clock_session.completed_at = utc_now()
    elif event_type == "reset":
        _ensure_not_terminal(clock_session, "reset")
        remaining_ms = clock_session.base_seconds * 1000
        clock_session.white_remaining_ms = remaining_ms
        clock_session.black_remaining_ms = remaining_ms
        clock_session.active_color = "none"
        clock_session.status = "setup"
        clock_session.result = None
        clock_session.started_at = None
        clock_session.completed_at = None
    elif event_type == "cancel":
        _ensure_not_terminal(clock_session, "cancel")
        _apply_snapshot(clock_session, payload)
        clock_session.status = "cancelled"
        clock_session.result = "aborted"
        clock_session.active_color = "none"
        clock_session.completed_at = utc_now()
    else:
        raise ValueError(f"Unsupported clock event {event_type}")

    await _record_event(
        session=session,
        clock_session=clock_session,
        event_type=event_type,
        actor_user_id=user.id,
        client_timestamp=getattr(payload, "client_timestamp", None),
        metadata=metadata,
    )
    await session.commit()
    await session.refresh(clock_session)
    return ClockSessionResponse.model_validate(clock_session)


async def start_clock_session(
    session: AsyncSession,
    user: User,
    clock_session_id: uuid.UUID,
    payload: ClockStartRequest,
) -> ClockSessionResponse:
    return await _mutate_clock_session(session, user, clock_session_id, "start", payload)


async def pause_clock_session(
    session: AsyncSession,
    user: User,
    clock_session_id: uuid.UUID,
    payload: ClockSnapshotRequest,
) -> ClockSessionResponse:
    return await _mutate_clock_session(session, user, clock_session_id, "pause", payload)


async def resume_clock_session(
    session: AsyncSession,
    user: User,
    clock_session_id: uuid.UUID,
    payload: ClockResumeRequest,
) -> ClockSessionResponse:
    return await _mutate_clock_session(session, user, clock_session_id, "resume", payload)


async def switch_clock_turn(
    session: AsyncSession,
    user: User,
    clock_session_id: uuid.UUID,
    payload: ClockSwitchTurnRequest,
) -> ClockSessionResponse:
    return await _mutate_clock_session(session, user, clock_session_id, "switch_turn", payload)


async def adjust_clock_session(
    session: AsyncSession,
    user: User,
    clock_session_id: uuid.UUID,
    payload: ClockAdjustRequest,
) -> ClockSessionResponse:
    metadata = {"reason": payload.reason} if payload.reason else {}
    return await _mutate_clock_session(
        session,
        user,
        clock_session_id,
        "adjust_time",
        payload,
        metadata=metadata,
    )


async def flag_clock_session(
    session: AsyncSession,
    user: User,
    clock_session_id: uuid.UUID,
    payload: ClockFlagRequest,
) -> ClockSessionResponse:
    return await _mutate_clock_session(
        session,
        user,
        clock_session_id,
        "flag",
        payload,
        metadata={"flagged_color": payload.flagged_color},
    )


async def complete_clock_session(
    session: AsyncSession,
    user: User,
    clock_session_id: uuid.UUID,
    payload: ClockCompleteRequest,
) -> ClockSessionResponse:
    return await _mutate_clock_session(
        session,
        user,
        clock_session_id,
        "complete",
        payload,
        metadata={"result": payload.result},
    )


async def reset_clock_session(
    session: AsyncSession,
    user: User,
    clock_session_id: uuid.UUID,
    payload: ClockResetRequest,
) -> ClockSessionResponse:
    return await _mutate_clock_session(session, user, clock_session_id, "reset", payload)


async def cancel_clock_session(
    session: AsyncSession,
    user: User,
    clock_session_id: uuid.UUID,
    payload: ClockCancelRequest,
) -> ClockSessionResponse:
    metadata = {"reason": payload.reason} if payload.reason else {}
    return await _mutate_clock_session(
        session,
        user,
        clock_session_id,
        "cancel",
        payload,
        metadata=metadata,
    )


def _admin_clock_filters(
    statement: Select[tuple[ClockSession]],
    status_filter: str | None,
    tournament_id: uuid.UUID | None,
    pairing_id: uuid.UUID | None,
    created_by: uuid.UUID | None,
) -> Select[tuple[ClockSession]]:
    if status_filter is not None:
        statement = statement.where(ClockSession.status == status_filter)
    if tournament_id is not None:
        statement = statement.where(ClockSession.tournament_id == tournament_id)
    if pairing_id is not None:
        statement = statement.where(ClockSession.pairing_id == pairing_id)
    if created_by is not None:
        statement = statement.where(ClockSession.created_by == created_by)
    return statement


async def list_admin_clock_sessions(
    session: AsyncSession,
    status_filter: str | None = None,
    tournament_id: uuid.UUID | None = None,
    pairing_id: uuid.UUID | None = None,
    created_by: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ClockSessionListResponse:
    statement = _admin_clock_filters(
        select(ClockSession),
        status_filter,
        tournament_id,
        pairing_id,
        created_by,
    )
    total = await session.scalar(select(func.count()).select_from(statement.subquery()))
    result = await session.execute(
        statement.order_by(ClockSession.created_at.desc(), ClockSession.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return ClockSessionListResponse(
        items=[ClockSessionResponse.model_validate(item) for item in result.scalars()],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


async def get_admin_clock_session(
    session: AsyncSession,
    clock_session_id: uuid.UUID,
) -> ClockSessionResponse:
    clock_session = await session.get(ClockSession, clock_session_id)
    if clock_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clock session not found")
    return ClockSessionResponse.model_validate(clock_session)


async def list_admin_clock_events(
    session: AsyncSession,
    clock_session_id: uuid.UUID,
    limit: int = 100,
    offset: int = 0,
) -> ClockEventListResponse:
    clock_session = await session.get(ClockSession, clock_session_id)
    if clock_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clock session not found")
    statement = select(ClockEvent).where(ClockEvent.clock_session_id == clock_session.id)
    total = await session.scalar(select(func.count()).select_from(statement.subquery()))
    result = await session.execute(
        statement.order_by(ClockEvent.server_timestamp.asc(), ClockEvent.id.asc())
        .limit(limit)
        .offset(offset)
    )
    return ClockEventListResponse(
        items=[_event_response(event) for event in result.scalars()],
        limit=limit,
        offset=offset,
        total=total or 0,
    )
