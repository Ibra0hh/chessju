import asyncio
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from decimal import Decimal
from typing import Any

import chess
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin import models as admin_models  # noqa: F401
from app.analysis.engine import (
    PositionAnalysis,
    StockfishEngine,
    classify_centipawn_loss,
)
from app.analysis.models import AnalysisJob, AnalysisMoveEvaluation, AnalysisReport
from app.auth import models as auth_models  # noqa: F401
from app.common.time import utc_now
from app.config import get_settings
from app.database import AsyncSessionLocal
from app.files import models as files_models  # noqa: F401
from app.games.models import GameMove
from app.leaderboard import models as leaderboard_models  # noqa: F401
from app.news import models as news_models  # noqa: F401
from app.notifications import models as notification_models  # noqa: F401
from app.notifications.services import create_user_notification
from app.pgn import models as pgn_models  # noqa: F401
from app.realtime import models as realtime_models  # noqa: F401
from app.tournaments import models as tournaments_models  # noqa: F401
from app.users import models as users_models  # noqa: F401

AnalysisEngineFactory = Callable[[], AbstractContextManager[Any]]


def _safe_error_message(exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    return message[:500]


def _centipawn_loss(before: PositionAnalysis, after: PositionAnalysis) -> int | None:
    if before.side_score_cp is None or after.side_score_cp is None:
        return None
    return max(0, before.side_score_cp - after.side_score_cp)


def _accuracy(losses: list[int]) -> Decimal | None:
    if not losses:
        return None
    average_loss = sum(losses) / len(losses)
    return Decimal(str(round(max(0.0, 100.0 - (average_loss / 5.0)), 2)))


def _empty_summary() -> dict[str, Any]:
    classifications = {
        "book": 0,
        "best": 0,
        "excellent": 0,
        "good": 0,
        "inaccuracy": 0,
        "mistake": 0,
        "blunder": 0,
        "forced": 0,
        "unknown": 0,
    }
    return {
        "total_plies": 0,
        "white": classifications.copy(),
        "black": classifications.copy(),
    }


def _default_engine_factory() -> AbstractContextManager[StockfishEngine]:
    settings = get_settings()
    return StockfishEngine(path=settings.stockfish_path)


async def _load_job(session: AsyncSession, job_id: uuid.UUID) -> AnalysisJob | None:
    return await session.get(AnalysisJob, job_id)


async def _load_moves(session: AsyncSession, game_id: uuid.UUID) -> list[GameMove]:
    result = await session.execute(
        select(GameMove).where(GameMove.game_id == game_id).order_by(GameMove.ply_number.asc())
    )
    return list(result.scalars())


async def _mark_failed(session: AsyncSession, job_id: uuid.UUID, exc: Exception) -> None:
    job = await _load_job(session, job_id)
    if job is None:
        return
    job.status = "failed"
    job.error_message = _safe_error_message(exc)
    job.completed_at = utc_now()
    await create_user_notification(
        session,
        user_id=job.requested_by,
        notification_type="analysis.failed",
        title="Analysis failed",
        body="Game analysis could not be completed",
        data={"analysis_job_id": job.id, "game_id": job.game_id},
    )
    await session.commit()


async def _set_running(session: AsyncSession, job: AnalysisJob) -> None:
    job.status = "running"
    job.started_at = utc_now()
    job.error_message = None
    await session.commit()


async def _store_report(
    session: AsyncSession,
    job: AnalysisJob,
    summary: dict[str, Any],
    final_evaluation: dict[str, Any] | None,
    white_accuracy: Decimal | None,
    black_accuracy: Decimal | None,
    move_rows: list[dict[str, Any]],
    engine_version: str | None,
) -> None:
    await session.execute(delete(AnalysisReport).where(AnalysisReport.analysis_job_id == job.id))
    report = AnalysisReport(
        game_id=job.game_id,
        analysis_job_id=job.id,
        summary=summary,
        white_accuracy=white_accuracy,
        black_accuracy=black_accuracy,
        final_evaluation=final_evaluation,
    )
    session.add(report)
    await session.flush()
    session.add_all(
        [
            AnalysisMoveEvaluation(
                analysis_report_id=report.id,
                game_move_id=row["game_move_id"],
                ply_number=row["ply_number"],
                side=row["side"],
                san=row["san"],
                uci=row["uci"],
                evaluation_before=row["evaluation_before"],
                evaluation_after=row["evaluation_after"],
                best_move_uci=row["best_move_uci"],
                best_move_san=row["best_move_san"],
                principal_variation=row["principal_variation"],
                centipawn_loss=row["centipawn_loss"],
                classification=row["classification"],
            )
            for row in move_rows
        ]
    )
    job.status = "completed"
    job.engine_version = engine_version
    job.completed_at = utc_now()
    job.error_message = None
    await create_user_notification(
        session,
        user_id=job.requested_by,
        notification_type="analysis.completed",
        title="Analysis completed",
        body="Your game analysis is ready",
        data={"analysis_job_id": job.id, "game_id": job.game_id, "analysis_report_id": report.id},
    )
    await session.commit()


async def run_analysis_job_async(
    job_id: uuid.UUID,
    analyzer_factory: AnalysisEngineFactory | None = None,
) -> None:
    try:
        async with AsyncSessionLocal() as session:
            job = await _load_job(session, job_id)
            if job is None or job.status not in {"queued", "running"}:
                return
            await _set_running(session, job)

        async with AsyncSessionLocal() as session:
            job = await _load_job(session, job_id)
            if job is None:
                return
            moves = await _load_moves(session, job.game_id)
            settings = get_settings()
            if not moves:
                raise ValueError("Game has no moves to analyze")
            if len(moves) > settings.analysis_max_plies:
                raise ValueError("Game exceeds analysis ply limit")

            summary = _empty_summary()
            final_evaluation: dict[str, Any] | None = None
            move_rows: list[dict[str, Any]] = []
            losses_by_side: dict[str, list[int]] = {"white": [], "black": []}
            factory = analyzer_factory or _default_engine_factory
            engine_version: str | None = None

            with factory() as analyzer:
                engine_version = getattr(analyzer, "version", None)
                for move in moves:
                    board_before = chess.Board(move.fen_before)
                    actual_move = chess.Move.from_uci(move.uci)
                    pov_color = chess.WHITE if move.side == "white" else chess.BLACK
                    before = analyzer.analyze(board_before, job.depth or 10, pov_color)
                    if actual_move not in board_before.legal_moves:
                        raise ValueError("Stored game move is not legal for its FEN")
                    board_before.push(actual_move)
                    after = analyzer.analyze(board_before, job.depth or 10, pov_color)
                    loss = _centipawn_loss(before, after)
                    classification = classify_centipawn_loss(loss)
                    summary[move.side][classification] += 1
                    summary["total_plies"] += 1
                    if loss is not None:
                        losses_by_side[move.side].append(loss)
                    final_evaluation = after.evaluation
                    move_rows.append(
                        {
                            "game_move_id": move.id,
                            "ply_number": move.ply_number,
                            "side": move.side,
                            "san": move.san,
                            "uci": move.uci,
                            "evaluation_before": before.evaluation,
                            "evaluation_after": after.evaluation,
                            "best_move_uci": before.best_move_uci,
                            "best_move_san": before.best_move_san,
                            "principal_variation": before.principal_variation,
                            "centipawn_loss": loss,
                            "classification": classification,
                        }
                    )

            await _store_report(
                session=session,
                job=job,
                summary=summary,
                final_evaluation=final_evaluation,
                white_accuracy=_accuracy(losses_by_side["white"]),
                black_accuracy=_accuracy(losses_by_side["black"]),
                move_rows=move_rows,
                engine_version=engine_version,
            )
    except Exception as exc:
        async with AsyncSessionLocal() as session:
            await _mark_failed(session, job_id, exc)


def run_analysis_job(job_id: str) -> None:
    asyncio.run(run_analysis_job_async(uuid.UUID(job_id)))
