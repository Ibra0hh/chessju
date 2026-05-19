import uuid

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin
from app.chesscom.schemas import (
    AdminChessComAccountListResponse,
    AdminChessComImportedGameListResponse,
    ChessComAccountResponse,
    ChessComConnectRequest,
    ChessComImportedGameListResponse,
    ChessComSyncJobListResponse,
    ChessComSyncJobResponse,
    ChessComSyncRequest,
)
from app.chesscom.services import (
    connect_account,
    disconnect_account,
    get_account,
    get_user_sync_job,
    list_admin_accounts,
    list_admin_imported_games,
    list_admin_sync_jobs,
    list_user_imported_games,
    list_user_sync_jobs,
    request_sync,
)
from app.common.rate_limit import enforce_user_rate_limit
from app.config import get_settings
from app.database import get_db_session
from app.users.models import User

router = APIRouter(tags=["Chess.com"])


@router.post("/integrations/chesscom/connect", response_model=ChessComAccountResponse)
async def connect_chesscom_account(
    payload: ChessComConnectRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ChessComAccountResponse:
    return await connect_account(session=session, user=current_user, username=payload.username)


@router.get("/integrations/chesscom/account", response_model=ChessComAccountResponse | None)
async def chesscom_account(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ChessComAccountResponse | None:
    return await get_account(session=session, user_id=current_user.id)


@router.delete("/integrations/chesscom/account", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_chesscom_account(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    await disconnect_account(session=session, user_id=current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/integrations/chesscom/sync",
    response_model=ChessComSyncJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def sync_chesscom_games(
    payload: ChessComSyncRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ChessComSyncJobResponse:
    settings = get_settings()
    await enforce_user_rate_limit(
        request,
        user=current_user,
        scope="chesscom_sync",
        limit=settings.rate_limit_chesscom_sync_per_hour,
        window_seconds=3600,
    )
    return await request_sync(session=session, user=current_user, months=payload.months)


@router.get("/integrations/chesscom/sync-jobs", response_model=ChessComSyncJobListResponse)
async def my_chesscom_sync_jobs(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ChessComSyncJobListResponse:
    return await list_user_sync_jobs(
        session=session,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/integrations/chesscom/sync-jobs/{job_id}",
    response_model=ChessComSyncJobResponse,
)
async def my_chesscom_sync_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ChessComSyncJobResponse:
    return await get_user_sync_job(session=session, user_id=current_user.id, job_id=job_id)


@router.get(
    "/integrations/chesscom/imported-games",
    response_model=ChessComImportedGameListResponse,
)
async def my_chesscom_imported_games(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ChessComImportedGameListResponse:
    return await list_user_imported_games(
        session=session,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )


@router.get("/admin/chesscom/accounts", response_model=AdminChessComAccountListResponse)
async def admin_chesscom_accounts(
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AdminChessComAccountListResponse:
    _ = current_admin
    return await list_admin_accounts(session=session, limit=limit, offset=offset)


@router.get("/admin/chesscom/sync-jobs", response_model=ChessComSyncJobListResponse)
async def admin_chesscom_sync_jobs(
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    status_filter: str | None = Query(default=None, alias="status"),
    user_id: uuid.UUID | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ChessComSyncJobListResponse:
    _ = current_admin
    return await list_admin_sync_jobs(
        session=session,
        status_filter=status_filter,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/admin/chesscom/imported-games",
    response_model=AdminChessComImportedGameListResponse,
)
async def admin_chesscom_imported_games(
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AdminChessComImportedGameListResponse:
    _ = current_admin
    return await list_admin_imported_games(session=session, limit=limit, offset=offset)
