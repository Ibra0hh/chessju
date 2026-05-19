"""chess clock backend

Revision ID: 0011_chess_clock_backend
Revises: 0010_chesscom_import
Create Date: 2026-05-19 00:00:11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0011_chess_clock_backend"
down_revision: str | None = "0010_chesscom_import"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "clock_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("pairing_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("white_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("black_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("base_seconds", sa.Integer(), nullable=False),
        sa.Column("increment_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("delay_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("white_remaining_ms", sa.Integer(), nullable=False),
        sa.Column("black_remaining_ms", sa.Integer(), nullable=False),
        sa.Column("active_color", sa.Text(), nullable=False, server_default="none"),
        sa.Column("status", sa.Text(), nullable=False, server_default="setup"),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("base_seconds > 0", name="ck_clock_sessions_base_seconds_positive"),
        sa.CheckConstraint(
            "increment_seconds >= 0",
            name="ck_clock_sessions_increment_seconds_non_negative",
        ),
        sa.CheckConstraint(
            "delay_seconds >= 0",
            name="ck_clock_sessions_delay_seconds_non_negative",
        ),
        sa.CheckConstraint(
            "white_remaining_ms >= 0",
            name="ck_clock_sessions_white_remaining_non_negative",
        ),
        sa.CheckConstraint(
            "black_remaining_ms >= 0",
            name="ck_clock_sessions_black_remaining_non_negative",
        ),
        sa.CheckConstraint(
            "active_color in ('white', 'black', 'none')",
            name="ck_clock_sessions_active_color_valid",
        ),
        sa.CheckConstraint(
            "status in ('setup', 'running', 'paused', 'completed', 'cancelled')",
            name="ck_clock_sessions_status_valid",
        ),
        sa.CheckConstraint(
            (
                "result is null or result in ('white_flagged', 'black_flagged', "
                "'white_win', 'black_win', 'draw', 'aborted', 'manual')"
            ),
            name="ck_clock_sessions_result_valid",
        ),
        sa.ForeignKeyConstraint(["black_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["pairing_id"], ["pairings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["white_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_clock_sessions_tournament_id", "clock_sessions", ["tournament_id"])
    op.create_index("ix_clock_sessions_pairing_id", "clock_sessions", ["pairing_id"])
    op.create_index("ix_clock_sessions_white_user_id", "clock_sessions", ["white_user_id"])
    op.create_index("ix_clock_sessions_black_user_id", "clock_sessions", ["black_user_id"])
    op.create_index("ix_clock_sessions_status", "clock_sessions", ["status"])
    op.create_index("ix_clock_sessions_created_by", "clock_sessions", ["created_by"])

    op.create_table(
        "clock_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clock_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("white_remaining_ms", sa.Integer(), nullable=False),
        sa.Column("black_remaining_ms", sa.Integer(), nullable=False),
        sa.Column("active_color", sa.Text(), nullable=False),
        sa.Column("client_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "server_timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.CheckConstraint(
            (
                "event_type in ('setup', 'start', 'pause', 'resume', 'switch_turn', "
                "'adjust_time', 'flag', 'reset', 'complete', 'cancel')"
            ),
            name="ck_clock_events_event_type_valid",
        ),
        sa.CheckConstraint(
            "white_remaining_ms >= 0",
            name="ck_clock_events_white_remaining_non_negative",
        ),
        sa.CheckConstraint(
            "black_remaining_ms >= 0",
            name="ck_clock_events_black_remaining_non_negative",
        ),
        sa.CheckConstraint(
            "active_color in ('white', 'black', 'none')",
            name="ck_clock_events_active_color_valid",
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["clock_session_id"], ["clock_sessions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_clock_events_clock_session_id", "clock_events", ["clock_session_id"])
    op.create_index("ix_clock_events_event_type", "clock_events", ["event_type"])
    op.create_index("ix_clock_events_server_timestamp", "clock_events", ["server_timestamp"])


def downgrade() -> None:
    op.drop_index("ix_clock_events_server_timestamp", table_name="clock_events")
    op.drop_index("ix_clock_events_event_type", table_name="clock_events")
    op.drop_index("ix_clock_events_clock_session_id", table_name="clock_events")
    op.drop_table("clock_events")
    op.drop_index("ix_clock_sessions_created_by", table_name="clock_sessions")
    op.drop_index("ix_clock_sessions_status", table_name="clock_sessions")
    op.drop_index("ix_clock_sessions_black_user_id", table_name="clock_sessions")
    op.drop_index("ix_clock_sessions_white_user_id", table_name="clock_sessions")
    op.drop_index("ix_clock_sessions_pairing_id", table_name="clock_sessions")
    op.drop_index("ix_clock_sessions_tournament_id", table_name="clock_sessions")
    op.drop_table("clock_sessions")
