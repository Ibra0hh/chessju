import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.time import utc_now
from app.database import Base


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"
    __table_args__ = (
        CheckConstraint(
            "status in ('queued', 'running', 'completed', 'failed', 'cancelled')",
            name="ck_analysis_jobs_status_valid",
        ),
        CheckConstraint("depth is null or depth > 0", name="ck_analysis_jobs_depth_positive"),
        CheckConstraint(
            "time_limit_ms is null or time_limit_ms > 0",
            name="ck_analysis_jobs_time_limit_positive",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued", index=True)
    engine_name: Mapped[str] = mapped_column(Text, nullable=False, default="stockfish")
    engine_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    depth: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_limit_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    white_accuracy: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    black_accuracy: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    final_evaluation: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class AnalysisMoveEvaluation(Base):
    __tablename__ = "analysis_move_evaluations"
    __table_args__ = (
        UniqueConstraint(
            "analysis_report_id",
            "ply_number",
            name="uq_analysis_move_evaluations_report_ply",
        ),
        CheckConstraint("ply_number > 0", name="ck_analysis_move_evaluations_ply_positive"),
        CheckConstraint(
            "side in ('white', 'black')",
            name="ck_analysis_move_evaluations_side_valid",
        ),
        CheckConstraint(
            (
                "classification is null or classification in ('book', 'best', 'excellent', "
                "'good', 'inaccuracy', 'mistake', 'blunder', 'forced', 'unknown')"
            ),
            name="ck_analysis_move_evaluations_classification_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    analysis_report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    game_move_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_moves.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ply_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    side: Mapped[str] = mapped_column(Text, nullable=False)
    san: Mapped[str] = mapped_column(Text, nullable=False)
    uci: Mapped[str] = mapped_column(Text, nullable=False)
    evaluation_before: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    evaluation_after: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    best_move_uci: Mapped[str | None] = mapped_column(Text, nullable=True)
    best_move_san: Mapped[str | None] = mapped_column(Text, nullable=True)
    principal_variation: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    centipawn_loss: Mapped[int | None] = mapped_column(Integer, nullable=True)
    classification: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
