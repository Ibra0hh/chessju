"""tournaments mvp

Revision ID: 0005_tournaments_mvp
Revises: 0004_files_news_announcements
Create Date: 2026-05-19 00:00:05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005_tournaments_mvp"
down_revision: str | None = "0004_files_news_announcements"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "time_controls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("base_seconds", sa.Integer(), nullable=False),
        sa.Column("increment_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("delay_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("base_seconds > 0", name="ck_time_controls_base_seconds_positive"),
        sa.CheckConstraint(
            "increment_seconds >= 0",
            name="ck_time_controls_increment_seconds_non_negative",
        ),
        sa.CheckConstraint(
            "delay_seconds >= 0",
            name="ck_time_controls_delay_seconds_non_negative",
        ),
        sa.CheckConstraint(
            "type in ('bullet', 'blitz', 'rapid', 'classical', 'custom')",
            name="ck_time_controls_type_valid",
        ),
    )
    op.create_index("ix_time_controls_type", "time_controls", ["type"])

    op.create_table(
        "tournaments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("format", sa.Text(), nullable=False),
        sa.Column("time_control_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("max_players", sa.Integer(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("registration_open_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("registration_close_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cover_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            (
                "status in ('draft', 'published', 'registration_open', "
                "'registration_closed', 'check_in', 'in_progress', 'completed', "
                "'cancelled')"
            ),
            name="ck_tournaments_status_valid",
        ),
        sa.CheckConstraint(
            "format in ('swiss', 'round_robin', 'knockout', 'arena', 'manual')",
            name="ck_tournaments_format_valid",
        ),
        sa.CheckConstraint(
            "max_players is null or max_players > 0",
            name="ck_tournaments_max_players_positive",
        ),
        sa.ForeignKeyConstraint(["cover_file_id"], ["files.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["time_control_id"], ["time_controls.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_tournaments_slug", "tournaments", ["slug"], unique=True)
    op.create_index("ix_tournaments_status", "tournaments", ["status"])
    op.create_index("ix_tournaments_starts_at", "tournaments", ["starts_at"])
    op.create_index("ix_tournaments_deleted_at", "tournaments", ["deleted_at"])
    op.create_index("ix_tournaments_created_by", "tournaments", ["created_by"])

    op.create_table(
        "tournament_registrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("seed_rating", sa.Integer(), nullable=True),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status in ('pending', 'approved', 'waitlisted', 'cancelled', 'rejected')",
            name="ck_tournament_registrations_status_valid",
        ),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tournament_id", "user_id", name="uq_tournament_registrations_user"),
    )
    op.create_index(
        "ix_tournament_registrations_tournament_id",
        "tournament_registrations",
        ["tournament_id"],
    )
    op.create_index(
        "ix_tournament_registrations_user_id",
        "tournament_registrations",
        ["user_id"],
    )
    op.create_index(
        "ix_tournament_registrations_status",
        "tournament_registrations",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_tournament_registrations_status", table_name="tournament_registrations")
    op.drop_index("ix_tournament_registrations_user_id", table_name="tournament_registrations")
    op.drop_index(
        "ix_tournament_registrations_tournament_id",
        table_name="tournament_registrations",
    )
    op.drop_table("tournament_registrations")
    op.drop_index("ix_tournaments_created_by", table_name="tournaments")
    op.drop_index("ix_tournaments_deleted_at", table_name="tournaments")
    op.drop_index("ix_tournaments_starts_at", table_name="tournaments")
    op.drop_index("ix_tournaments_status", table_name="tournaments")
    op.drop_index("ix_tournaments_slug", table_name="tournaments")
    op.drop_table("tournaments")
    op.drop_index("ix_time_controls_type", table_name="time_controls")
    op.drop_table("time_controls")
