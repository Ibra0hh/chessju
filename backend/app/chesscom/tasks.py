import asyncio
import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin import models as admin_models  # noqa: F401
from app.analysis import models as analysis_models  # noqa: F401
from app.auth import models as auth_models  # noqa: F401
from app.chesscom.client import ChessComApiClient
from app.chesscom.models import ChessComAccount, ChessComImportedGame, ChessComSyncJob
from app.chesscom.services import safe_error_message, timestamp_to_datetime
from app.common.time import utc_now
from app.database import AsyncSessionLocal
from app.files import models as files_models  # noqa: F401
from app.leaderboard import models as leaderboard_models  # noqa: F401
from app.news import models as news_models  # noqa: F401
from app.pgn import models as pgn_models  # noqa: F401
from app.pgn.services import create_game_from_parsed_pgn, parse_pgn_text
from app.tournaments import models as tournaments_models  # noqa: F401
from app.users import models as users_models  # noqa: F401


def _result_from_payload(payload: dict[str, Any], parsed_result: str | None) -> str | None:
    if parsed_result and parsed_result != "*":
        return parsed_result
    white = payload.get("white")
    black = payload.get("black")
    white_result = white.get("result") if isinstance(white, dict) else None
    black_result = black.get("result") if isinstance(black, dict) else None
    if white_result == "win":
        return "1-0"
    if black_result == "win":
        return "0-1"
    if white_result in {"agreed", "repetition", "stalemate", "insufficient", "50move"}:
        return "1/2-1/2"
    return parsed_result


def _player_username(payload: dict[str, Any], color: str) -> str | None:
    player = payload.get(color)
    if isinstance(player, dict) and player.get("username"):
        return str(player["username"])
    return None


async def _load_sync_job(
    session: AsyncSession,
    sync_job_id: uuid.UUID,
) -> ChessComSyncJob | None:
    return await session.get(ChessComSyncJob, sync_job_id)


async def _set_running(session: AsyncSession, job: ChessComSyncJob) -> None:
    job.status = "running"
    job.started_at = utc_now()
    job.error_message = None
    await session.commit()


async def _mark_failed(session: AsyncSession, sync_job_id: uuid.UUID, exc: Exception) -> None:
    job = await _load_sync_job(session, sync_job_id)
    if job is None:
        return
    job.status = "failed"
    job.error_message = safe_error_message(exc)
    job.completed_at = utc_now()
    await session.commit()


async def _is_duplicate(session: AsyncSession, chesscom_url: str) -> bool:
    result = await session.execute(
        select(ChessComImportedGame.id).where(ChessComImportedGame.chesscom_url == chesscom_url)
    )
    return result.scalar_one_or_none() is not None


async def _import_game_payload(
    session: AsyncSession,
    job: ChessComSyncJob,
    account: ChessComAccount,
    payload: dict[str, Any],
) -> bool:
    pgn_text = payload.get("pgn")
    chesscom_url = payload.get("url")
    if not isinstance(pgn_text, str) or not pgn_text.strip() or not isinstance(chesscom_url, str):
        return False
    if await _is_duplicate(session, chesscom_url):
        return False

    parsed = parse_pgn_text(pgn_text)
    game = await create_game_from_parsed_pgn(
        session=session,
        user_id=job.user_id,
        pgn_text=pgn_text,
        parsed=parsed,
        import_source="chesscom",
        game_source="chesscom_import",
    )
    played_at = timestamp_to_datetime(payload.get("end_time")) or parsed.played_at
    game.played_at = played_at
    game.result = _result_from_payload(payload, parsed.metadata.get("Result"))
    game.game_metadata = {
        **game.game_metadata,
        "ChessComUrl": chesscom_url,
        "ChessComTimeClass": str(payload.get("time_class"))
        if payload.get("time_class") is not None
        else "",
    }
    imported_game = ChessComImportedGame(
        user_id=job.user_id,
        chesscom_account_id=account.id,
        game_id=game.id,
        chesscom_url=chesscom_url,
        chesscom_uuid=str(payload.get("uuid")) if payload.get("uuid") else None,
        played_at=played_at,
        time_class=str(payload.get("time_class")) if payload.get("time_class") else None,
        time_control=str(payload.get("time_control")) if payload.get("time_control") else None,
        rated=payload.get("rated") if isinstance(payload.get("rated"), bool) else None,
        white_username=_player_username(payload, "white"),
        black_username=_player_username(payload, "black"),
        result=game.result,
    )
    session.add(imported_game)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return False
    return True


async def _import_payload_safely(
    session: AsyncSession,
    job: ChessComSyncJob,
    account: ChessComAccount,
    payload: dict[str, Any],
) -> bool:
    try:
        return await _import_game_payload(session, job, account, payload)
    except (HTTPException, ValueError, AssertionError):
        await session.rollback()
        return False


async def run_chesscom_sync_job_async(
    sync_job_id: uuid.UUID,
    api_client: ChessComApiClient | None = None,
) -> None:
    try:
        async with AsyncSessionLocal() as session:
            job = await _load_sync_job(session, sync_job_id)
            if job is None or job.status not in {"queued", "running"}:
                return
            await _set_running(session, job)

        async with AsyncSessionLocal() as session:
            job = await _load_sync_job(session, sync_job_id)
            if job is None:
                return
            account = await session.get(ChessComAccount, job.chesscom_account_id)
            if account is None or account.disconnected_at is not None:
                raise ValueError("Chess.com account is not connected")

            client = api_client or ChessComApiClient()
            archives = await client.fetch_archives(account.username)
            archive_limit = job.archive_months_requested or 0
            selected_archives = sorted(archives)[-archive_limit:] if archive_limit else []

            games_found = 0
            games_imported = 0
            games_skipped = 0
            for archive_url in selected_archives:
                games = await client.fetch_archive_games(archive_url)
                for payload in games:
                    games_found += 1
                    if await _import_payload_safely(session, job, account, payload):
                        games_imported += 1
                    else:
                        games_skipped += 1

            job.games_found = games_found
            job.games_imported = games_imported
            job.games_skipped = games_skipped
            job.status = "completed"
            job.completed_at = utc_now()
            job.error_message = None
            account.last_synced_at = utc_now()
            await session.commit()
    except Exception as exc:
        async with AsyncSessionLocal() as session:
            await _mark_failed(session, sync_job_id, exc)


def sync_chesscom_games(sync_job_id: str) -> None:
    asyncio.run(run_chesscom_sync_job_async(uuid.UUID(sync_job_id)))
