import uuid

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.models import AnalysisJob, AnalysisMoveEvaluation, AnalysisReport
from app.analysis.queue import enqueue_analysis_job
from app.analysis.schemas import (
    AnalysisJobListResponse,
    AnalysisJobResponse,
    AnalysisReportListResponse,
    AnalysisReportResponse,
    AnalysisReportSummaryResponse,
    GameAnalysisResponse,
)
from app.common.time import utc_now
from app.config import get_settings
from app.games.models import Game, GameMove
from app.pgn.services import get_authorized_game
from app.users.models import Profile, User


def _validate_depth(depth: int | None) -> int:
    settings = get_settings()
    resolved_depth = depth or settings.stockfish_depth_default
    if resolved_depth < 1 or resolved_depth > settings.stockfish_depth_max:
        raise HTTPException(
            status_code=422,
            detail=f"depth must be between 1 and {settings.stockfish_depth_max}",
        )
    return resolved_depth


async def _moves_count(session: AsyncSession, game_id: uuid.UUID) -> int:
    count = await session.scalar(
        select(func.count()).select_from(GameMove).where(GameMove.game_id == game_id)
    )
    return count or 0


async def _get_completed_job_for_depth(
    session: AsyncSession,
    game_id: uuid.UUID,
    depth: int,
) -> AnalysisJob | None:
    result = await session.execute(
        select(AnalysisJob)
        .join(AnalysisReport, AnalysisReport.analysis_job_id == AnalysisJob.id)
        .where(
            AnalysisJob.game_id == game_id,
            AnalysisJob.depth == depth,
            AnalysisJob.status == "completed",
        )
        .order_by(AnalysisJob.completed_at.desc(), AnalysisJob.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_active_job_for_user(
    session: AsyncSession,
    game_id: uuid.UUID,
    user_id: uuid.UUID,
    depth: int,
) -> AnalysisJob | None:
    result = await session.execute(
        select(AnalysisJob)
        .where(
            AnalysisJob.game_id == game_id,
            AnalysisJob.requested_by == user_id,
            AnalysisJob.depth == depth,
            AnalysisJob.status.in_(("queued", "running")),
        )
        .order_by(AnalysisJob.created_at.desc(), AnalysisJob.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def request_game_analysis(
    session: AsyncSession,
    user: User,
    game_id: uuid.UUID,
    depth: int | None = None,
) -> AnalysisJobResponse:
    game = await get_authorized_game(session, user, game_id)
    resolved_depth = _validate_depth(depth)
    moves_count = await _moves_count(session, game.id)
    if moves_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game has no moves to analyze",
        )
    settings = get_settings()
    if moves_count > settings.analysis_max_plies:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Game exceeds analysis ply limit",
        )

    completed_job = await _get_completed_job_for_depth(session, game.id, resolved_depth)
    if completed_job is not None:
        return AnalysisJobResponse.model_validate(completed_job)

    active_job = await _get_active_job_for_user(session, game.id, user.id, resolved_depth)
    if active_job is not None:
        return AnalysisJobResponse.model_validate(active_job)

    job = AnalysisJob(
        game_id=game.id,
        requested_by=user.id,
        status="queued",
        engine_name="stockfish",
        depth=resolved_depth,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    try:
        enqueue_analysis_job(job.id)
    except Exception as exc:
        job.status = "failed"
        job.error_message = "Failed to enqueue analysis job"
        job.completed_at = utc_now()
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analysis queue is unavailable",
        ) from exc

    return AnalysisJobResponse.model_validate(job)


async def _get_authorized_analysis_job(
    session: AsyncSession,
    user: User,
    job_id: uuid.UUID,
) -> AnalysisJob:
    job = await session.get(AnalysisJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis job not found")
    await get_authorized_game(session, user, job.game_id)
    return job


async def get_analysis_job(
    session: AsyncSession,
    user: User,
    job_id: uuid.UUID,
) -> AnalysisJobResponse:
    job = await _get_authorized_analysis_job(session, user, job_id)
    return AnalysisJobResponse.model_validate(job)


async def _latest_report_for_game(
    session: AsyncSession,
    game_id: uuid.UUID,
) -> AnalysisReport | None:
    result = await session.execute(
        select(AnalysisReport)
        .where(AnalysisReport.game_id == game_id)
        .order_by(AnalysisReport.created_at.desc(), AnalysisReport.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _latest_job_for_game(
    session: AsyncSession,
    game_id: uuid.UUID,
) -> AnalysisJob | None:
    result = await session.execute(
        select(AnalysisJob)
        .where(AnalysisJob.game_id == game_id)
        .order_by(AnalysisJob.created_at.desc(), AnalysisJob.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _report_moves(
    session: AsyncSession,
    report_id: uuid.UUID,
) -> list[AnalysisMoveEvaluation]:
    result = await session.execute(
        select(AnalysisMoveEvaluation)
        .where(AnalysisMoveEvaluation.analysis_report_id == report_id)
        .order_by(AnalysisMoveEvaluation.ply_number.asc())
    )
    return list(result.scalars())


async def build_report_response(
    session: AsyncSession,
    report: AnalysisReport,
) -> AnalysisReportResponse:
    moves = await _report_moves(session, report.id)
    game_moves_result = await session.execute(
        select(GameMove.ply_number, GameMove.move_number).where(GameMove.game_id == report.game_id)
    )
    move_numbers = {ply_number: move_number for ply_number, move_number in game_moves_result.all()}
    return AnalysisReportResponse(
        id=report.id,
        game_id=report.game_id,
        analysis_job_id=report.analysis_job_id,
        white_accuracy=float(report.white_accuracy) if report.white_accuracy is not None else None,
        black_accuracy=float(report.black_accuracy) if report.black_accuracy is not None else None,
        summary=report.summary,
        final_evaluation=report.final_evaluation,
        created_at=report.created_at,
        moves=[
            {
                "id": move.id,
                "game_move_id": move.game_move_id,
                "ply_number": move.ply_number,
                "move_number": move_numbers.get(move.ply_number),
                "side": move.side,
                "san": move.san,
                "uci": move.uci,
                "evaluation_before": move.evaluation_before,
                "evaluation_after": move.evaluation_after,
                "best_move_uci": move.best_move_uci,
                "best_move_san": move.best_move_san,
                "principal_variation": move.principal_variation,
                "centipawn_loss": move.centipawn_loss,
                "classification": move.classification,
                "created_at": move.created_at,
            }
            for move in moves
        ],
    )


async def get_game_analysis(
    session: AsyncSession,
    user: User,
    game_id: uuid.UUID,
) -> GameAnalysisResponse:
    game = await get_authorized_game(session, user, game_id)
    report = await _latest_report_for_game(session, game.id)
    if report is not None:
        return GameAnalysisResponse(report=await build_report_response(session, report), job=None)
    job = await _latest_job_for_game(session, game.id)
    return GameAnalysisResponse(
        report=None,
        job=AnalysisJobResponse.model_validate(job) if job is not None else None,
    )


async def get_analysis_report(
    session: AsyncSession,
    user: User,
    report_id: uuid.UUID,
) -> AnalysisReportResponse:
    report = await session.get(AnalysisReport, report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis report not found",
        )
    await get_authorized_game(session, user, report.game_id)
    return await build_report_response(session, report)


def _job_filters(
    statement: Select[tuple[AnalysisJob]],
    status_filter: str | None,
    game_id: uuid.UUID | None,
    requested_by: uuid.UUID | None,
) -> Select[tuple[AnalysisJob]]:
    if status_filter is not None:
        statement = statement.where(AnalysisJob.status == status_filter)
    if game_id is not None:
        statement = statement.where(AnalysisJob.game_id == game_id)
    if requested_by is not None:
        statement = statement.where(AnalysisJob.requested_by == requested_by)
    return statement


async def list_admin_analysis_jobs(
    session: AsyncSession,
    status_filter: str | None = None,
    game_id: uuid.UUID | None = None,
    requested_by: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> AnalysisJobListResponse:
    statement = _job_filters(select(AnalysisJob), status_filter, game_id, requested_by)
    count_statement = _job_filters(
        select(func.count()).select_from(AnalysisJob),
        status_filter,
        game_id,
        requested_by,
    )
    total = await session.scalar(count_statement)
    result = await session.execute(
        statement.order_by(AnalysisJob.created_at.desc(), AnalysisJob.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return AnalysisJobListResponse(
        items=[AnalysisJobResponse.model_validate(job) for job in result.scalars()],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


def _report_filters(
    statement: Select[tuple[AnalysisReport]],
    game_id: uuid.UUID | None,
) -> Select[tuple[AnalysisReport]]:
    if game_id is not None:
        statement = statement.where(AnalysisReport.game_id == game_id)
    return statement


async def list_admin_analysis_reports(
    session: AsyncSession,
    game_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> AnalysisReportListResponse:
    statement = _report_filters(select(AnalysisReport), game_id)
    count_statement = _report_filters(select(func.count()).select_from(AnalysisReport), game_id)
    total = await session.scalar(count_statement)
    result = await session.execute(
        statement.order_by(AnalysisReport.created_at.desc(), AnalysisReport.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return AnalysisReportListResponse(
        items=[
            AnalysisReportSummaryResponse(
                id=report.id,
                game_id=report.game_id,
                analysis_job_id=report.analysis_job_id,
                white_accuracy=(
                    float(report.white_accuracy) if report.white_accuracy is not None else None
                ),
                black_accuracy=(
                    float(report.black_accuracy) if report.black_accuracy is not None else None
                ),
                summary=report.summary,
                final_evaluation=report.final_evaluation,
                created_at=report.created_at,
            )
            for report in result.scalars()
        ],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


async def user_can_view_game(session: AsyncSession, user: User, game: Game) -> bool:
    try:
        await get_authorized_game(session, user, game.id)
    except HTTPException:
        return False
    return True


async def profile_for_user(session: AsyncSession, user_id: uuid.UUID) -> Profile | None:
    result = await session.execute(select(Profile).where(Profile.user_id == user_id))
    return result.scalar_one_or_none()
