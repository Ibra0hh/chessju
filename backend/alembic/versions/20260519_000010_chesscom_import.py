"""chesscom import

Revision ID: 0010_chesscom_import
Revises: 0009_stockfish_analysis_jobs
Create Date: 2026-05-19 00:00:10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0010_chesscom_import"
down_revision: str | None = "0009_stockfish_analysis_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_pgn_imports_source_valid", "pgn_imports", type_="check")
    op.create_check_constraint(
        "ck_pgn_imports_source_valid",
        "pgn_imports",
        "source in ('paste', 'file_upload', 'chesscom')",
    )

    op.create_table(
        "chesscom_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("profile_url", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("last_online_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disconnected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_chesscom_accounts_user_id"),
        sa.UniqueConstraint("username", name="uq_chesscom_accounts_username"),
    )
    op.create_index("ix_chesscom_accounts_user_id", "chesscom_accounts", ["user_id"])
    op.create_index("ix_chesscom_accounts_username", "chesscom_accounts", ["username"])

    op.create_table(
        "chesscom_sync_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chesscom_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="queued"),
        sa.Column("archive_months_requested", sa.Integer(), nullable=True),
        sa.Column("games_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("games_imported", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("games_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status in ('queued', 'running', 'completed', 'failed', 'cancelled')",
            name="ck_chesscom_sync_jobs_status_valid",
        ),
        sa.CheckConstraint(
            "archive_months_requested is null or archive_months_requested > 0",
            name="ck_chesscom_sync_jobs_months_positive",
        ),
        sa.CheckConstraint(
            "games_found >= 0",
            name="ck_chesscom_sync_jobs_games_found_nonnegative",
        ),
        sa.CheckConstraint(
            "games_imported >= 0",
            name="ck_chesscom_sync_jobs_games_imported_nonnegative",
        ),
        sa.CheckConstraint(
            "games_skipped >= 0",
            name="ck_chesscom_sync_jobs_games_skipped_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["chesscom_account_id"],
            ["chesscom_accounts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_chesscom_sync_jobs_user_id", "chesscom_sync_jobs", ["user_id"])
    op.create_index("ix_chesscom_sync_jobs_status", "chesscom_sync_jobs", ["status"])

    op.create_table(
        "chesscom_imported_games",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chesscom_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chesscom_url", sa.Text(), nullable=False),
        sa.Column("chesscom_uuid", sa.Text(), nullable=True),
        sa.Column("played_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("time_class", sa.Text(), nullable=True),
        sa.Column("time_control", sa.Text(), nullable=True),
        sa.Column("rated", sa.Boolean(), nullable=True),
        sa.Column("white_username", sa.Text(), nullable=True),
        sa.Column("black_username", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["chesscom_account_id"],
            ["chesscom_accounts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("chesscom_url", name="uq_chesscom_imported_games_url"),
        sa.UniqueConstraint("game_id", name="uq_chesscom_imported_games_game_id"),
    )
    op.create_index("ix_chesscom_imported_games_user_id", "chesscom_imported_games", ["user_id"])
    op.create_index(
        "ix_chesscom_imported_games_chesscom_account_id",
        "chesscom_imported_games",
        ["chesscom_account_id"],
    )
    op.create_index(
        "ix_chesscom_imported_games_game_id",
        "chesscom_imported_games",
        ["game_id"],
    )
    op.create_index(
        "ix_chesscom_imported_games_played_at",
        "chesscom_imported_games",
        ["played_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_chesscom_imported_games_played_at", table_name="chesscom_imported_games")
    op.drop_index("ix_chesscom_imported_games_game_id", table_name="chesscom_imported_games")
    op.drop_index(
        "ix_chesscom_imported_games_chesscom_account_id",
        table_name="chesscom_imported_games",
    )
    op.drop_index("ix_chesscom_imported_games_user_id", table_name="chesscom_imported_games")
    op.drop_table("chesscom_imported_games")
    op.drop_index("ix_chesscom_sync_jobs_status", table_name="chesscom_sync_jobs")
    op.drop_index("ix_chesscom_sync_jobs_user_id", table_name="chesscom_sync_jobs")
    op.drop_table("chesscom_sync_jobs")
    op.drop_index("ix_chesscom_accounts_username", table_name="chesscom_accounts")
    op.drop_index("ix_chesscom_accounts_user_id", table_name="chesscom_accounts")
    op.drop_table("chesscom_accounts")
    op.drop_constraint("ck_pgn_imports_source_valid", "pgn_imports", type_="check")
    op.create_check_constraint(
        "ck_pgn_imports_source_valid",
        "pgn_imports",
        "source in ('paste', 'file_upload')",
    )
