"""rounds pairings results

Revision ID: 0006_rounds_pairings_results
Revises: 0005_tournaments_mvp
Create Date: 2026-05-19 00:00:06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006_rounds_pairings_results"
down_revision: str | None = "0005_tournaments_mvp"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rounds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("round_number > 0", name="ck_rounds_round_number_positive"),
        sa.CheckConstraint(
            "status in ('draft', 'published', 'in_progress', 'completed', 'cancelled')",
            name="ck_rounds_status_valid",
        ),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tournament_id", "round_number", name="uq_rounds_tournament_number"),
    )
    op.create_index("ix_rounds_tournament_id", "rounds", ["tournament_id"])
    op.create_index("ix_rounds_status", "rounds", ["status"])

    op.create_table(
        "pairings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("round_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("board_number", sa.Integer(), nullable=False),
        sa.Column("white_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("black_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="scheduled"),
        sa.Column("result", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("result_reported_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("result_reported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("board_number > 0", name="ck_pairings_board_number_positive"),
        sa.CheckConstraint(
            "white_user_id is null or black_user_id is null or white_user_id <> black_user_id",
            name="ck_pairings_distinct_players",
        ),
        sa.CheckConstraint(
            "status in ('scheduled', 'active', 'completed', 'disputed', 'cancelled')",
            name="ck_pairings_status_valid",
        ),
        sa.CheckConstraint(
            (
                "result in ('pending', 'white_win', 'black_win', 'draw', 'white_forfeit', "
                "'black_forfeit', 'double_forfeit', 'bye')"
            ),
            name="ck_pairings_result_valid",
        ),
        sa.ForeignKeyConstraint(["black_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["result_reported_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["round_id"], ["rounds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["white_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("round_id", "board_number", name="uq_pairings_round_board"),
    )
    op.create_index("ix_pairings_round_id", "pairings", ["round_id"])
    op.create_index("ix_pairings_tournament_id", "pairings", ["tournament_id"])
    op.create_index("ix_pairings_white_user_id", "pairings", ["white_user_id"])
    op.create_index("ix_pairings_black_user_id", "pairings", ["black_user_id"])
    op.create_index("ix_pairings_status", "pairings", ["status"])
    op.create_index("ix_pairings_result", "pairings", ["result"])

    op.create_table(
        "games",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("pairing_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("round_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("white_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("black_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("white_name", sa.Text(), nullable=True),
        sa.Column("black_name", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False, server_default="tournament"),
        sa.Column("pgn_text", sa.Text(), nullable=True),
        sa.Column("pgn_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("played_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("eco_code", sa.Text(), nullable=True),
        sa.Column("opening_name", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "source in ('tournament', 'pgn_upload', 'chesscom_import', 'manual')",
            name="ck_games_source_valid",
        ),
        sa.ForeignKeyConstraint(["black_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["pairing_id"], ["pairings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["pgn_file_id"], ["files.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["round_id"], ["rounds.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["white_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_games_tournament_id", "games", ["tournament_id"])
    op.create_index("ix_games_round_id", "games", ["round_id"])
    op.create_index("ix_games_pairing_id", "games", ["pairing_id"])
    op.create_index("ix_games_white_user_id", "games", ["white_user_id"])
    op.create_index("ix_games_black_user_id", "games", ["black_user_id"])
    op.create_index("ix_games_source", "games", ["source"])


def downgrade() -> None:
    op.drop_index("ix_games_source", table_name="games")
    op.drop_index("ix_games_black_user_id", table_name="games")
    op.drop_index("ix_games_white_user_id", table_name="games")
    op.drop_index("ix_games_pairing_id", table_name="games")
    op.drop_index("ix_games_round_id", table_name="games")
    op.drop_index("ix_games_tournament_id", table_name="games")
    op.drop_table("games")
    op.drop_index("ix_pairings_result", table_name="pairings")
    op.drop_index("ix_pairings_status", table_name="pairings")
    op.drop_index("ix_pairings_black_user_id", table_name="pairings")
    op.drop_index("ix_pairings_white_user_id", table_name="pairings")
    op.drop_index("ix_pairings_tournament_id", table_name="pairings")
    op.drop_index("ix_pairings_round_id", table_name="pairings")
    op.drop_table("pairings")
    op.drop_index("ix_rounds_status", table_name="rounds")
    op.drop_index("ix_rounds_tournament_id", table_name="rounds")
    op.drop_table("rounds")
