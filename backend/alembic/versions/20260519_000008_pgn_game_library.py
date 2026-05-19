"""pgn game library

Revision ID: 0008_pgn_game_library
Revises: 0007_ju_leaderboard
Create Date: 2026-05-19 00:00:08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008_pgn_game_library"
down_revision: str | None = "0007_ju_leaderboard"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("games", sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column(
        "games",
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column("games", sa.Column("initial_fen", sa.Text(), nullable=True))
    op.add_column("games", sa.Column("final_fen", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_games_owner_id_users",
        "games",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_games_owner_id", "games", ["owner_id"])
    op.create_index("ix_games_created_at", "games", ["created_at"])

    op.create_table(
        "game_moves",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ply_number", sa.Integer(), nullable=False),
        sa.Column("move_number", sa.Integer(), nullable=False),
        sa.Column("side", sa.Text(), nullable=False),
        sa.Column("san", sa.Text(), nullable=False),
        sa.Column("uci", sa.Text(), nullable=False),
        sa.Column("fen_before", sa.Text(), nullable=False),
        sa.Column("fen_after", sa.Text(), nullable=False),
        sa.Column("is_check", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_checkmate", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("ply_number > 0", name="ck_game_moves_ply_number_positive"),
        sa.CheckConstraint("move_number > 0", name="ck_game_moves_move_number_positive"),
        sa.CheckConstraint("side in ('white', 'black')", name="ck_game_moves_side_valid"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("game_id", "ply_number", name="uq_game_moves_game_ply"),
    )
    op.create_index("ix_game_moves_game_id", "game_moves", ["game_id"])
    op.create_index("ix_game_moves_ply_number", "game_moves", ["ply_number"])

    op.create_table(
        "pgn_imports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "source in ('paste', 'file_upload')",
            name="ck_pgn_imports_source_valid",
        ),
        sa.CheckConstraint(
            "status in ('pending', 'parsed', 'failed')",
            name="ck_pgn_imports_status_valid",
        ),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_pgn_imports_user_id", "pgn_imports", ["user_id"])
    op.create_index("ix_pgn_imports_status", "pgn_imports", ["status"])
    op.create_index("ix_pgn_imports_game_id", "pgn_imports", ["game_id"])


def downgrade() -> None:
    op.drop_index("ix_pgn_imports_game_id", table_name="pgn_imports")
    op.drop_index("ix_pgn_imports_status", table_name="pgn_imports")
    op.drop_index("ix_pgn_imports_user_id", table_name="pgn_imports")
    op.drop_table("pgn_imports")
    op.drop_index("ix_game_moves_ply_number", table_name="game_moves")
    op.drop_index("ix_game_moves_game_id", table_name="game_moves")
    op.drop_table("game_moves")
    op.drop_index("ix_games_created_at", table_name="games")
    op.drop_index("ix_games_owner_id", table_name="games")
    op.drop_constraint("fk_games_owner_id_users", "games", type_="foreignkey")
    op.drop_column("games", "final_fen")
    op.drop_column("games", "initial_fen")
    op.drop_column("games", "metadata")
    op.drop_column("games", "owner_id")
