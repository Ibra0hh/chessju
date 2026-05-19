import uuid

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, oauth2_scheme, require_admin
from app.auth.security import decode_access_token
from app.database import get_db_session
from app.tournaments.schemas import (
    AdminTournamentListResponse,
    AdminTournamentResponse,
    DeleteTournamentResponse,
    TimeControlCreateRequest,
    TimeControlListResponse,
    TimeControlResponse,
    TimeControlUpdateRequest,
    TournamentCreateRequest,
    TournamentDetailResponse,
    TournamentListResponse,
    TournamentRegistrationListResponse,
    TournamentRegistrationResponse,
    TournamentRegistrationUpdateRequest,
    TournamentUpdateRequest,
    UserTournamentRegistrationListResponse,
)
from app.tournaments.services import (
    build_admin_tournament_response,
    cancel_current_user_registration,
    create_time_control,
    create_tournament,
    get_admin_tournament,
    get_public_tournament_by_slug,
    list_admin_tournaments,
    list_public_tournaments,
    list_time_controls,
    list_tournament_registrations,
    list_user_tournament_registrations,
    register_for_tournament,
    set_tournament_status,
    soft_delete_tournament,
    update_registration_status,
    update_time_control,
    update_tournament,
)
from app.users.models import User
from app.users.services import get_user_with_profile

router = APIRouter(tags=["tournaments"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


async def get_optional_current_user(
    token: str | None = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User | None:
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(str(payload["sub"]))
    except (KeyError, ValueError, jwt.InvalidTokenError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    user = await get_user_with_profile(session, user_id)
    if user is None or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@router.get("/tournaments", response_model=TournamentListResponse)
async def public_tournaments(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
) -> TournamentListResponse:
    return await list_public_tournaments(
        session=session,
        limit=limit,
        offset=offset,
        status_filter=status_filter,
    )


@router.get("/tournaments/{slug}", response_model=TournamentDetailResponse)
async def public_tournament_detail(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> TournamentDetailResponse:
    user_id = current_user.id if current_user else None
    return await get_public_tournament_by_slug(session, slug, user_id)


@router.post(
    "/tournaments/{tournament_id}/register",
    response_model=TournamentRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_current_user_for_tournament(
    tournament_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> TournamentRegistrationResponse:
    return await register_for_tournament(session, current_user.id, tournament_id)


@router.delete(
    "/tournaments/{tournament_id}/registration",
    response_model=TournamentRegistrationResponse,
)
async def cancel_own_tournament_registration(
    tournament_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> TournamentRegistrationResponse:
    return await cancel_current_user_registration(session, current_user.id, tournament_id)


@router.get(
    "/users/me/tournament-registrations",
    response_model=UserTournamentRegistrationListResponse,
)
async def my_tournament_registrations(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> UserTournamentRegistrationListResponse:
    return await list_user_tournament_registrations(
        session=session,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/admin/time-controls",
    response_model=TimeControlResponse,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_time_control(
    payload: TimeControlCreateRequest,
    request: Request,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> TimeControlResponse:
    return await create_time_control(
        session=session,
        admin_id=current_admin.id,
        payload=payload,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/admin/time-controls", response_model=TimeControlListResponse)
async def admin_list_time_controls(
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> TimeControlListResponse:
    _ = current_admin
    return await list_time_controls(session, limit=limit, offset=offset)


@router.patch("/admin/time-controls/{time_control_id}", response_model=TimeControlResponse)
async def admin_update_time_control(
    time_control_id: uuid.UUID,
    payload: TimeControlUpdateRequest,
    request: Request,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> TimeControlResponse:
    return await update_time_control(
        session=session,
        admin_id=current_admin.id,
        time_control_id=time_control_id,
        payload=payload,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.post(
    "/admin/tournaments",
    response_model=AdminTournamentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_tournament(
    payload: TournamentCreateRequest,
    request: Request,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> AdminTournamentResponse:
    return await create_tournament(
        session=session,
        admin_id=current_admin.id,
        payload=payload,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/admin/tournaments", response_model=AdminTournamentListResponse)
async def admin_list_tournaments(
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    include_deleted: bool = False,
) -> AdminTournamentListResponse:
    _ = current_admin
    return await list_admin_tournaments(
        session=session,
        limit=limit,
        offset=offset,
        status_filter=status_filter,
        include_deleted=include_deleted,
    )


@router.get("/admin/tournaments/{tournament_id}", response_model=AdminTournamentResponse)
async def admin_get_tournament(
    tournament_id: uuid.UUID,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> AdminTournamentResponse:
    _ = current_admin
    tournament = await get_admin_tournament(session, tournament_id)
    return await build_admin_tournament_response(session, tournament)


@router.patch("/admin/tournaments/{tournament_id}", response_model=AdminTournamentResponse)
async def admin_update_tournament(
    tournament_id: uuid.UUID,
    payload: TournamentUpdateRequest,
    request: Request,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> AdminTournamentResponse:
    return await update_tournament(
        session=session,
        admin_id=current_admin.id,
        tournament_id=tournament_id,
        payload=payload,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/admin/tournaments/{tournament_id}/publish", response_model=AdminTournamentResponse)
async def admin_publish_tournament(
    tournament_id: uuid.UUID,
    request: Request,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> AdminTournamentResponse:
    return await set_tournament_status(
        session=session,
        admin_id=current_admin.id,
        tournament_id=tournament_id,
        next_status="published",
        action="tournament.published",
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.post(
    "/admin/tournaments/{tournament_id}/open-registration",
    response_model=AdminTournamentResponse,
)
async def admin_open_tournament_registration(
    tournament_id: uuid.UUID,
    request: Request,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> AdminTournamentResponse:
    return await set_tournament_status(
        session=session,
        admin_id=current_admin.id,
        tournament_id=tournament_id,
        next_status="registration_open",
        action="tournament.registration_opened",
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.post(
    "/admin/tournaments/{tournament_id}/close-registration",
    response_model=AdminTournamentResponse,
)
async def admin_close_tournament_registration(
    tournament_id: uuid.UUID,
    request: Request,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> AdminTournamentResponse:
    return await set_tournament_status(
        session=session,
        admin_id=current_admin.id,
        tournament_id=tournament_id,
        next_status="registration_closed",
        action="tournament.registration_closed",
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/admin/tournaments/{tournament_id}/cancel", response_model=AdminTournamentResponse)
async def admin_cancel_tournament(
    tournament_id: uuid.UUID,
    request: Request,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> AdminTournamentResponse:
    return await set_tournament_status(
        session=session,
        admin_id=current_admin.id,
        tournament_id=tournament_id,
        next_status="cancelled",
        action="tournament.cancelled",
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.delete("/admin/tournaments/{tournament_id}", response_model=DeleteTournamentResponse)
async def admin_delete_tournament(
    tournament_id: uuid.UUID,
    request: Request,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> DeleteTournamentResponse:
    return await soft_delete_tournament(
        session=session,
        admin_id=current_admin.id,
        tournament_id=tournament_id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.get(
    "/admin/tournaments/{tournament_id}/registrations",
    response_model=TournamentRegistrationListResponse,
)
async def admin_list_tournament_registrations(
    tournament_id: uuid.UUID,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
) -> TournamentRegistrationListResponse:
    _ = current_admin
    return await list_tournament_registrations(
        session=session,
        tournament_id=tournament_id,
        limit=limit,
        offset=offset,
        status_filter=status_filter,
    )


@router.patch(
    "/admin/tournament-registrations/{registration_id}",
    response_model=TournamentRegistrationResponse,
)
async def admin_update_tournament_registration(
    registration_id: uuid.UUID,
    payload: TournamentRegistrationUpdateRequest,
    request: Request,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> TournamentRegistrationResponse:
    return await update_registration_status(
        session=session,
        admin_id=current_admin.id,
        registration_id=registration_id,
        payload=payload,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
