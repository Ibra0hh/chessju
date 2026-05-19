import re
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.chesscom.client import ChessComApiClient
from app.chesscom.models import ChessComAccount, ChessComImportedGame, ChessComSyncJob
from app.chesscom.queue import enqueue_chesscom_sync_job
from app.chesscom.schemas import (
    AdminChessComAccountListResponse,
    AdminChessComAccountResponse,
    AdminChessComImportedGameListResponse,
    AdminChessComImportedGameResponse,
    ChessComAccountResponse,
    ChessComImportedGameListResponse,
    ChessComImportedGameResponse,
    ChessComSyncJobListResponse,
    ChessComSyncJobResponse,
)
from app.common.time import utc_now
from app.config import get_settings
from app.users.models import Profile, User

USERNAME_RE = re.compile(r"^[a-z0-9_-]{2,50}$")


def normalize_chesscom_username(value: str) -> str:
    username = value.strip().rstrip("/")
    if "/" in username:
        username = username.split("/")[-1]
    if username.startswith("@"):
        username = username[1:]
    username = username.strip().lower()
    if not USERNAME_RE.fullmatch(username):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid Chess.com username",
        )
    return username


def timestamp_to_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=UTC)
    except (TypeError, ValueError, OSError):
        return None


def safe_error_message(exc: Exception) -> str:
    if isinstance(exc, HTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else "Chess.com request failed"
        return detail[:500]
    return (str(exc).strip() or exc.__class__.__name__)[:500]


def get_chesscom_api_client() -> ChessComApiClient:
    return ChessComApiClient()


async def _active_account_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> ChessComAccount | None:
    result = await session.execute(
        select(ChessComAccount).where(
            ChessComAccount.user_id == user_id,
            ChessComAccount.disconnected_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def _profile_for_user(session: AsyncSession, user_id: uuid.UUID) -> Profile | None:
    result = await session.execute(select(Profile).where(Profile.user_id == user_id))
    return result.scalar_one_or_none()


def _apply_profile_data(account: ChessComAccount, username: str, data: dict[str, Any]) -> None:
    account.username = normalize_chesscom_username(str(data.get("username") or username))
    account.profile_url = str(data.get("url")) if data.get("url") else None
    account.title = str(data.get("title")) if data.get("title") else None
    account.country = str(data.get("country")) if data.get("country") else None
    account.avatar_url = str(data.get("avatar")) if data.get("avatar") else None
    account.last_online_at = timestamp_to_datetime(data.get("last_online"))
    account.joined_at = timestamp_to_datetime(data.get("joined"))
    account.verified = True
    account.disconnected_at = None


async def connect_account(
    session: AsyncSession,
    user: User,
    username: str,
    api_client: ChessComApiClient | None = None,
) -> ChessComAccountResponse:
    normalized_username = normalize_chesscom_username(username)
    client = api_client or get_chesscom_api_client()
    profile_data = await client.fetch_profile(normalized_username)
    canonical_username = normalize_chesscom_username(
        str(profile_data.get("username") or normalized_username)
    )

    conflicting_result = await session.execute(
        select(ChessComAccount).where(
            ChessComAccount.username == canonical_username,
            ChessComAccount.user_id != user.id,
        )
    )
    if conflicting_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Chess.com username is already connected",
        )

    account_result = await session.execute(
        select(ChessComAccount).where(ChessComAccount.user_id == user.id)
    )
    account = account_result.scalar_one_or_none()
    if account is None:
        account = ChessComAccount(user_id=user.id, username=canonical_username)
        session.add(account)
    _apply_profile_data(account, canonical_username, profile_data)

    profile = await _profile_for_user(session, user.id)
    if profile is not None:
        profile.chesscom_username = account.username

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Chess.com username is already connected",
        ) from exc
    await session.refresh(account)
    return ChessComAccountResponse.model_validate(account)


async def get_account(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> ChessComAccountResponse | None:
    account = await _active_account_for_user(session, user_id)
    return ChessComAccountResponse.model_validate(account) if account else None


async def disconnect_account(session: AsyncSession, user_id: uuid.UUID) -> bool:
    account = await _active_account_for_user(session, user_id)
    if account is None:
        return True
    account.disconnected_at = utc_now()
    account.verified = False
    profile = await _profile_for_user(session, user_id)
    if profile is not None:
        profile.chesscom_username = None
    await session.commit()
    return True


async def request_sync(
    session: AsyncSession,
    user: User,
    months: int | None,
) -> ChessComSyncJobResponse:
    account = await _active_account_for_user(session, user.id)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Connect a Chess.com account before syncing games",
        )

    active_result = await session.execute(
        select(ChessComSyncJob)
        .where(
            ChessComSyncJob.user_id == user.id,
            ChessComSyncJob.status.in_(("queued", "running")),
        )
        .order_by(ChessComSyncJob.created_at.desc(), ChessComSyncJob.id.desc())
        .limit(1)
    )
    active_job = active_result.scalar_one_or_none()
    if active_job is not None:
        return ChessComSyncJobResponse.model_validate(active_job)

    settings = get_settings()
    capped_months = min(
        months or settings.chesscom_sync_max_months,
        settings.chesscom_sync_max_months,
    )
    job = ChessComSyncJob(
        user_id=user.id,
        chesscom_account_id=account.id,
        status="queued",
        archive_months_requested=capped_months,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    try:
        enqueue_chesscom_sync_job(job.id)
    except Exception as exc:
        job.status = "failed"
        job.error_message = "Failed to enqueue Chess.com sync job"
        job.completed_at = utc_now()
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chess.com sync queue is unavailable",
        ) from exc

    return ChessComSyncJobResponse.model_validate(job)


async def get_user_sync_job(
    session: AsyncSession,
    user_id: uuid.UUID,
    job_id: uuid.UUID,
) -> ChessComSyncJobResponse:
    result = await session.execute(
        select(ChessComSyncJob).where(
            ChessComSyncJob.id == job_id,
            ChessComSyncJob.user_id == user_id,
        )
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sync job not found")
    return ChessComSyncJobResponse.model_validate(job)


async def list_user_sync_jobs(
    session: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> ChessComSyncJobListResponse:
    statement = select(ChessComSyncJob).where(ChessComSyncJob.user_id == user_id)
    total = await session.scalar(select(func.count()).select_from(statement.subquery()))
    result = await session.execute(
        statement.order_by(ChessComSyncJob.created_at.desc(), ChessComSyncJob.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return ChessComSyncJobListResponse(
        items=[ChessComSyncJobResponse.model_validate(job) for job in result.scalars()],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


async def list_user_imported_games(
    session: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> ChessComImportedGameListResponse:
    statement = select(ChessComImportedGame).where(ChessComImportedGame.user_id == user_id)
    total = await session.scalar(select(func.count()).select_from(statement.subquery()))
    result = await session.execute(
        statement.order_by(
            ChessComImportedGame.played_at.desc().nullslast(),
            ChessComImportedGame.created_at.desc(),
            ChessComImportedGame.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    return ChessComImportedGameListResponse(
        items=[
            ChessComImportedGameResponse.model_validate(imported_game)
            for imported_game in result.scalars()
        ],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


def _admin_jobs_statement(
    status_filter: str | None,
    user_id: uuid.UUID | None,
) -> Select[tuple[ChessComSyncJob]]:
    statement = select(ChessComSyncJob)
    if status_filter is not None:
        statement = statement.where(ChessComSyncJob.status == status_filter)
    if user_id is not None:
        statement = statement.where(ChessComSyncJob.user_id == user_id)
    return statement


async def list_admin_accounts(
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0,
) -> AdminChessComAccountListResponse:
    statement = select(ChessComAccount)
    total = await session.scalar(select(func.count()).select_from(statement.subquery()))
    result = await session.execute(
        statement.order_by(ChessComAccount.created_at.desc(), ChessComAccount.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return AdminChessComAccountListResponse(
        items=[
            AdminChessComAccountResponse.model_validate(account) for account in result.scalars()
        ],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


async def list_admin_sync_jobs(
    session: AsyncSession,
    status_filter: str | None = None,
    user_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ChessComSyncJobListResponse:
    statement = _admin_jobs_statement(status_filter, user_id)
    total = await session.scalar(select(func.count()).select_from(statement.subquery()))
    result = await session.execute(
        statement.order_by(ChessComSyncJob.created_at.desc(), ChessComSyncJob.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return ChessComSyncJobListResponse(
        items=[ChessComSyncJobResponse.model_validate(job) for job in result.scalars()],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


async def list_admin_imported_games(
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0,
) -> AdminChessComImportedGameListResponse:
    statement = select(ChessComImportedGame)
    total = await session.scalar(select(func.count()).select_from(statement.subquery()))
    result = await session.execute(
        statement.order_by(
            ChessComImportedGame.played_at.desc().nullslast(),
            ChessComImportedGame.created_at.desc(),
            ChessComImportedGame.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    return AdminChessComImportedGameListResponse(
        items=[
            AdminChessComImportedGameResponse.model_validate(imported_game)
            for imported_game in result.scalars()
        ],
        limit=limit,
        offset=offset,
        total=total or 0,
    )
