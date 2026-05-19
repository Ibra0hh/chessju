"""realtime notifications

Revision ID: 0013_realtime_notifications
Revises: 0012_friends_direct_chat
Create Date: 2026-05-19 00:00:13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0013_realtime_notifications"
down_revision: str | None = "0012_friends_direct_chat"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column(
            "data",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_type", "notifications", ["type"])
    op.create_index("ix_notifications_read_at", "notifications", ["read_at"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])

    op.create_table(
        "notification_preferences",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("in_app_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("tournament_updates", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("friend_requests", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("chat_messages", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("analysis_updates", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "chesscom_sync_updates",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("news_announcements", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(
        "ix_notification_preferences_user_id",
        "notification_preferences",
        ["user_id"],
    )

    op.create_table(
        "realtime_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_realtime_events_user_id", "realtime_events", ["user_id"])
    op.create_index("ix_realtime_events_channel", "realtime_events", ["channel"])
    op.create_index("ix_realtime_events_type", "realtime_events", ["type"])
    op.create_index("ix_realtime_events_created_at", "realtime_events", ["created_at"])
    op.create_index("ix_realtime_events_delivered_at", "realtime_events", ["delivered_at"])


def downgrade() -> None:
    op.drop_index("ix_realtime_events_delivered_at", table_name="realtime_events")
    op.drop_index("ix_realtime_events_created_at", table_name="realtime_events")
    op.drop_index("ix_realtime_events_type", table_name="realtime_events")
    op.drop_index("ix_realtime_events_channel", table_name="realtime_events")
    op.drop_index("ix_realtime_events_user_id", table_name="realtime_events")
    op.drop_table("realtime_events")
    op.drop_index("ix_notification_preferences_user_id", table_name="notification_preferences")
    op.drop_table("notification_preferences")
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_read_at", table_name="notifications")
    op.drop_index("ix_notifications_type", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
