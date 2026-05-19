import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin
from app.clock.schemas import (
    ClockAdjustRequest,
    ClockCancelRequest,
    ClockCompleteRequest,
    ClockEventListResponse,
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
from app.clock.services import (
    adjust_clock_session,
    cancel_clock_session,
    complete_clock_session,
    create_clock_session,
    flag_clock_session,
    get_admin_clock_session,
    get_clock_session,
    list_admin_clock_events,
    list_admin_clock_sessions,
    list_clock_events,
    pause_clock_session,
    reset_clock_session,
    resume_clock_session,
    start_clock_session,
    switch_clock_turn,
)
from app.database import get_db_session
from app.users.models import User

router = APIRouter(tags=["Clock"])


@router.post(
    "/clock/sessions",
    response_model=ClockSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_clock(
    payload: ClockSessionCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ClockSessionResponse:
    return await create_clock_session(session=session, user=current_user, payload=payload)


@router.get("/clock/sessions/{clock_session_id}", response_model=ClockSessionResponse)
async def clock_detail(
    clock_session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ClockSessionResponse:
    return await get_clock_session(
        session=session,
        user=current_user,
        clock_session_id=clock_session_id,
    )


@router.get("/clock/sessions/{clock_session_id}/events", response_model=ClockEventListResponse)
async def clock_events(
    clock_session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ClockEventListResponse:
    return await list_clock_events(
        session=session,
        user=current_user,
        clock_session_id=clock_session_id,
        limit=limit,
        offset=offset,
    )


@router.post("/clock/sessions/{clock_session_id}/start", response_model=ClockSessionResponse)
async def start_clock(
    clock_session_id: uuid.UUID,
    payload: ClockStartRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ClockSessionResponse:
    return await start_clock_session(session, current_user, clock_session_id, payload)


@router.post("/clock/sessions/{clock_session_id}/pause", response_model=ClockSessionResponse)
async def pause_clock(
    clock_session_id: uuid.UUID,
    payload: ClockSnapshotRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ClockSessionResponse:
    return await pause_clock_session(session, current_user, clock_session_id, payload)


@router.post("/clock/sessions/{clock_session_id}/resume", response_model=ClockSessionResponse)
async def resume_clock(
    clock_session_id: uuid.UUID,
    payload: ClockResumeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ClockSessionResponse:
    return await resume_clock_session(session, current_user, clock_session_id, payload)


@router.post("/clock/sessions/{clock_session_id}/switch-turn", response_model=ClockSessionResponse)
async def switch_turn(
    clock_session_id: uuid.UUID,
    payload: ClockSwitchTurnRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ClockSessionResponse:
    return await switch_clock_turn(session, current_user, clock_session_id, payload)


@router.post("/clock/sessions/{clock_session_id}/adjust", response_model=ClockSessionResponse)
async def adjust_clock(
    clock_session_id: uuid.UUID,
    payload: ClockAdjustRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ClockSessionResponse:
    return await adjust_clock_session(session, current_user, clock_session_id, payload)


@router.post("/clock/sessions/{clock_session_id}/flag", response_model=ClockSessionResponse)
async def flag_clock(
    clock_session_id: uuid.UUID,
    payload: ClockFlagRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ClockSessionResponse:
    return await flag_clock_session(session, current_user, clock_session_id, payload)


@router.post("/clock/sessions/{clock_session_id}/complete", response_model=ClockSessionResponse)
async def complete_clock(
    clock_session_id: uuid.UUID,
    payload: ClockCompleteRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ClockSessionResponse:
    return await complete_clock_session(session, current_user, clock_session_id, payload)


@router.post("/clock/sessions/{clock_session_id}/reset", response_model=ClockSessionResponse)
async def reset_clock(
    clock_session_id: uuid.UUID,
    payload: ClockResetRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ClockSessionResponse:
    return await reset_clock_session(session, current_user, clock_session_id, payload)


@router.post("/clock/sessions/{clock_session_id}/cancel", response_model=ClockSessionResponse)
async def cancel_clock(
    clock_session_id: uuid.UUID,
    payload: ClockCancelRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ClockSessionResponse:
    return await cancel_clock_session(session, current_user, clock_session_id, payload)


@router.get("/admin/clock/sessions", response_model=ClockSessionListResponse)
async def admin_clock_sessions(
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    status_filter: str | None = Query(default=None, alias="status"),
    tournament_id: uuid.UUID | None = None,
    pairing_id: uuid.UUID | None = None,
    created_by: uuid.UUID | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ClockSessionListResponse:
    _ = current_admin
    return await list_admin_clock_sessions(
        session=session,
        status_filter=status_filter,
        tournament_id=tournament_id,
        pairing_id=pairing_id,
        created_by=created_by,
        limit=limit,
        offset=offset,
    )


@router.get("/admin/clock/sessions/{clock_session_id}", response_model=ClockSessionResponse)
async def admin_clock_detail(
    clock_session_id: uuid.UUID,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> ClockSessionResponse:
    _ = current_admin
    return await get_admin_clock_session(session=session, clock_session_id=clock_session_id)


@router.get(
    "/admin/clock/sessions/{clock_session_id}/events",
    response_model=ClockEventListResponse,
)
async def admin_clock_events(
    clock_session_id: uuid.UUID,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ClockEventListResponse:
    _ = current_admin
    return await list_admin_clock_events(
        session=session,
        clock_session_id=clock_session_id,
        limit=limit,
        offset=offset,
    )
