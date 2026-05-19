import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin
from app.database import get_db_session
from app.leaderboard.schemas import (
    LeaderboardRecomputeRequest,
    LeaderboardResponse,
    SeasonCreateRequest,
    SeasonListResponse,
    SeasonResponse,
    SeasonUpdateRequest,
)
from app.leaderboard.services import (
    activate_season,
    create_season,
    get_default_public_leaderboard,
    get_leaderboard_for_season,
    list_seasons,
    recompute_leaderboard,
    update_season,
)
from app.users.models import User

router = APIRouter(tags=["leaderboard"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def public_leaderboard(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> LeaderboardResponse:
    return await get_default_public_leaderboard(session, limit=limit, offset=offset)


@router.get("/leaderboard/seasons", response_model=SeasonListResponse)
async def public_leaderboard_seasons(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> SeasonListResponse:
    return await list_seasons(session, limit=limit, offset=offset)


@router.get("/leaderboard/seasons/{season_id}", response_model=LeaderboardResponse)
async def public_leaderboard_for_season(
    season_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> LeaderboardResponse:
    return await get_leaderboard_for_season(
        session=session,
        season_id=season_id,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/admin/leaderboard/seasons",
    response_model=SeasonResponse,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_leaderboard_season(
    payload: SeasonCreateRequest,
    request: Request,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> SeasonResponse:
    return await create_season(
        session=session,
        admin_id=current_admin.id,
        payload=payload,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/admin/leaderboard/seasons", response_model=SeasonListResponse)
async def admin_list_leaderboard_seasons(
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> SeasonListResponse:
    _ = current_admin
    return await list_seasons(session, limit=limit, offset=offset)


@router.patch("/admin/leaderboard/seasons/{season_id}", response_model=SeasonResponse)
async def admin_update_leaderboard_season(
    season_id: uuid.UUID,
    payload: SeasonUpdateRequest,
    request: Request,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> SeasonResponse:
    return await update_season(
        session=session,
        admin_id=current_admin.id,
        season_id=season_id,
        payload=payload,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/admin/leaderboard/seasons/{season_id}/activate", response_model=SeasonResponse)
async def admin_activate_leaderboard_season(
    season_id: uuid.UUID,
    request: Request,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> SeasonResponse:
    return await activate_season(
        session=session,
        admin_id=current_admin.id,
        season_id=season_id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/admin/leaderboard/recompute", response_model=LeaderboardResponse)
async def admin_recompute_leaderboard(
    payload: LeaderboardRecomputeRequest,
    request: Request,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> LeaderboardResponse:
    return await recompute_leaderboard(
        session=session,
        admin_id=current_admin.id,
        season_id=payload.season_id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/admin/leaderboard", response_model=LeaderboardResponse)
async def admin_get_leaderboard(
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> LeaderboardResponse:
    _ = current_admin
    return await get_default_public_leaderboard(session, limit=limit, offset=offset)
