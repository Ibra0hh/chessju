"""stockfish analysis jobs

Revision ID: 0009_stockfish_analysis_jobs
Revises: 0008_pgn_game_library
Create Date: 2026-05-19 00:00:09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009_stockfish_analysis_jobs"
down_revision: str | None = "0008_pgn_game_library"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="queued"),
        sa.Column("engine_name", sa.Text(), nullable=False, server_default="stockfish"),
        sa.Column("engine_version", sa.Text(), nullable=True),
        sa.Column("depth", sa.Integer(), nullable=True),
        sa.Column("time_limit_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status in ('queued', 'running', 'completed', 'failed', 'cancelled')",
            name="ck_analysis_jobs_status_valid",
        ),
        sa.CheckConstraint("depth is null or depth > 0", name="ck_analysis_jobs_depth_positive"),
        sa.CheckConstraint(
            "time_limit_ms is null or time_limit_ms > 0",
            name="ck_analysis_jobs_time_limit_positive",
        ),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_analysis_jobs_game_id", "analysis_jobs", ["game_id"])
    op.create_index("ix_analysis_jobs_requested_by", "analysis_jobs", ["requested_by"])
    op.create_index("ix_analysis_jobs_status", "analysis_jobs", ["status"])
    op.create_index("ix_analysis_jobs_created_at", "analysis_jobs", ["created_at"])

    op.create_table(
        "analysis_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "summary",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("white_accuracy", sa.Numeric(5, 2), nullable=True),
        sa.Column("black_accuracy", sa.Numeric(5, 2), nullable=True),
        sa.Column("final_evaluation", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["analysis_job_id"], ["analysis_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_analysis_reports_game_id", "analysis_reports", ["game_id"])
    op.create_index(
        "ix_analysis_reports_analysis_job_id",
        "analysis_reports",
        ["analysis_job_id"],
    )

    op.create_table(
        "analysis_move_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("analysis_report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_move_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ply_number", sa.Integer(), nullable=False),
        sa.Column("side", sa.Text(), nullable=False),
        sa.Column("san", sa.Text(), nullable=False),
        sa.Column("uci", sa.Text(), nullable=False),
        sa.Column("evaluation_before", postgresql.JSONB(), nullable=True),
        sa.Column("evaluation_after", postgresql.JSONB(), nullable=True),
        sa.Column("best_move_uci", sa.Text(), nullable=True),
        sa.Column("best_move_san", sa.Text(), nullable=True),
        sa.Column("principal_variation", postgresql.JSONB(), nullable=True),
        sa.Column("centipawn_loss", sa.Integer(), nullable=True),
        sa.Column("classification", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "ply_number > 0",
            name="ck_analysis_move_evaluations_ply_positive",
        ),
        sa.CheckConstraint(
            "side in ('white', 'black')",
            name="ck_analysis_move_evaluations_side_valid",
        ),
        sa.CheckConstraint(
            (
                "classification is null or classification in ('book', 'best', 'excellent', "
                "'good', 'inaccuracy', 'mistake', 'blunder', 'forced', 'unknown')"
            ),
            name="ck_analysis_move_evaluations_classification_valid",
        ),
        sa.ForeignKeyConstraint(
            ["analysis_report_id"],
            ["analysis_reports.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["game_move_id"], ["game_moves.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "analysis_report_id",
            "ply_number",
            name="uq_analysis_move_evaluations_report_ply",
        ),
    )
    op.create_index(
        "ix_analysis_move_evaluations_analysis_report_id",
        "analysis_move_evaluations",
        ["analysis_report_id"],
    )
    op.create_index(
        "ix_analysis_move_evaluations_game_move_id",
        "analysis_move_evaluations",
        ["game_move_id"],
    )
    op.create_index(
        "ix_analysis_move_evaluations_ply_number",
        "analysis_move_evaluations",
        ["ply_number"],
    )
    op.create_index(
        "ix_analysis_move_evaluations_classification",
        "analysis_move_evaluations",
        ["classification"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_analysis_move_evaluations_classification",
        table_name="analysis_move_evaluations",
    )
    op.drop_index(
        "ix_analysis_move_evaluations_ply_number",
        table_name="analysis_move_evaluations",
    )
    op.drop_index(
        "ix_analysis_move_evaluations_game_move_id",
        table_name="analysis_move_evaluations",
    )
    op.drop_index(
        "ix_analysis_move_evaluations_analysis_report_id",
        table_name="analysis_move_evaluations",
    )
    op.drop_table("analysis_move_evaluations")
    op.drop_index("ix_analysis_reports_analysis_job_id", table_name="analysis_reports")
    op.drop_index("ix_analysis_reports_game_id", table_name="analysis_reports")
    op.drop_table("analysis_reports")
    op.drop_index("ix_analysis_jobs_created_at", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_status", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_requested_by", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_game_id", table_name="analysis_jobs")
    op.drop_table("analysis_jobs")
