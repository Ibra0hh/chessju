"""ju leaderboard

Revision ID: 0007_ju_leaderboard
Revises: 0006_rounds_pairings_results
Create Date: 2026-05-19 00:00:07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007_ju_leaderboard"
down_revision: str | None = "0006_rounds_pairings_results"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "seasons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "ends_at is null or ends_at > starts_at",
            name="ck_seasons_date_range_valid",
        ),
    )
    op.create_index("ix_seasons_active", "seasons", ["active"])
    op.create_index("ix_seasons_starts_at", "seasons", ["starts_at"])
    op.create_index("ix_seasons_ends_at", "seasons", ["ends_at"])
    op.create_index(
        "uq_seasons_one_active",
        "seasons",
        ["active"],
        unique=True,
        postgresql_where=sa.text("active = true"),
    )

    op.create_table(
        "player_ratings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating_type", sa.Text(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False, server_default="1200"),
        sa.Column("games_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "rating_type in ('internal', 'blitz', 'rapid', 'classical')",
            name="ck_player_ratings_type_valid",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_player_ratings_user_id", "player_ratings", ["user_id"])
    op.create_index("ix_player_ratings_rating_type", "player_ratings", ["rating_type"])
    op.create_index(
        "uq_player_ratings_user_type",
        "player_ratings",
        ["user_id", "rating_type"],
        unique=True,
    )

    op.create_table(
        "rating_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rating_type", sa.Text(), nullable=False, server_default="internal"),
        sa.Column("rating_before", sa.Integer(), nullable=False),
        sa.Column("rating_after", sa.Integer(), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "rating_type in ('internal', 'blitz', 'rapid', 'classical')",
            name="ck_rating_events_type_valid",
        ),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_rating_events_user_id", "rating_events", ["user_id"])
    op.create_index("ix_rating_events_game_id", "rating_events", ["game_id"])
    op.create_index("ix_rating_events_tournament_id", "rating_events", ["tournament_id"])

    op.create_table(
        "leaderboard_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("season_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("points", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("rating", sa.Integer(), nullable=False, server_default="1200"),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("draws", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("byes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("games_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tournaments_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "tie_breaks",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["season_id"], ["seasons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_leaderboard_snapshots_season_id", "leaderboard_snapshots", ["season_id"])
    op.create_index("ix_leaderboard_snapshots_user_id", "leaderboard_snapshots", ["user_id"])
    op.create_index("ix_leaderboard_snapshots_rank", "leaderboard_snapshots", ["rank"])
    op.create_index(
        "ix_leaderboard_snapshots_generated_at",
        "leaderboard_snapshots",
        ["generated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_leaderboard_snapshots_generated_at", table_name="leaderboard_snapshots")
    op.drop_index("ix_leaderboard_snapshots_rank", table_name="leaderboard_snapshots")
    op.drop_index("ix_leaderboard_snapshots_user_id", table_name="leaderboard_snapshots")
    op.drop_index("ix_leaderboard_snapshots_season_id", table_name="leaderboard_snapshots")
    op.drop_table("leaderboard_snapshots")
    op.drop_index("ix_rating_events_tournament_id", table_name="rating_events")
    op.drop_index("ix_rating_events_game_id", table_name="rating_events")
    op.drop_index("ix_rating_events_user_id", table_name="rating_events")
    op.drop_table("rating_events")
    op.drop_index("uq_player_ratings_user_type", table_name="player_ratings")
    op.drop_index("ix_player_ratings_rating_type", table_name="player_ratings")
    op.drop_index("ix_player_ratings_user_id", table_name="player_ratings")
    op.drop_table("player_ratings")
    op.drop_index("uq_seasons_one_active", table_name="seasons")
    op.drop_index("ix_seasons_ends_at", table_name="seasons")
    op.drop_index("ix_seasons_starts_at", table_name="seasons")
    op.drop_index("ix_seasons_active", table_name="seasons")
    op.drop_table("seasons")
