"""friends direct chat

Revision ID: 0012_friends_direct_chat
Revises: 0011_chess_clock_backend
Create Date: 2026-05-19 00:00:12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0012_friends_direct_chat"
down_revision: str | None = "0011_chess_clock_backend"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "friend_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("receiver_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("sender_id <> receiver_id", name="ck_friend_requests_not_self"),
        sa.CheckConstraint(
            "status in ('pending', 'accepted', 'rejected', 'cancelled')",
            name="ck_friend_requests_status_valid",
        ),
        sa.ForeignKeyConstraint(["receiver_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "sender_id",
            "receiver_id",
            name="uq_friend_requests_sender_receiver",
        ),
    )
    op.create_index("ix_friend_requests_sender_id", "friend_requests", ["sender_id"])
    op.create_index("ix_friend_requests_receiver_id", "friend_requests", ["receiver_id"])
    op.create_index("ix_friend_requests_status", "friend_requests", ["status"])

    op.create_table(
        "friendships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_a_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_b_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("user_a_id < user_b_id", name="ck_friendships_normalized_order"),
        sa.ForeignKeyConstraint(["user_a_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_b_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_a_id", "user_b_id", name="uq_friendships_user_pair"),
    )
    op.create_index("ix_friendships_user_a_id", "friendships", ["user_a_id"])
    op.create_index("ix_friendships_user_b_id", "friendships", ["user_b_id"])

    op.create_table(
        "blocked_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("blocker_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("blocked_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("blocker_id <> blocked_id", name="ck_blocked_users_not_self"),
        sa.ForeignKeyConstraint(["blocked_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["blocker_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("blocker_id", "blocked_id", name="uq_blocked_users_blocker_blocked"),
    )
    op.create_index("ix_blocked_users_blocker_id", "blocked_users", ["blocker_id"])
    op.create_index("ix_blocked_users_blocked_id", "blocked_users", ["blocked_id"])

    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("type", sa.Text(), nullable=False, server_default="direct"),
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
        sa.CheckConstraint("type in ('direct')", name="ck_conversations_type_valid"),
    )
    op.create_index("ix_conversations_type", "conversations", ["type"])

    op.create_table(
        "conversation_members",
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.Text(), nullable=False, server_default="member"),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "role in ('member', 'admin')",
            name="ck_conversation_members_role_valid",
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("conversation_id", "user_id"),
    )
    op.create_index("ix_conversation_members_user_id", "conversation_members", ["user_id"])

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("message_type", sa.Text(), nullable=False, server_default="text"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "message_type in ('text', 'system')",
            name="ck_messages_message_type_valid",
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_sender_id", "messages", ["sender_id"])
    op.create_index("ix_messages_created_at", "messages", ["created_at"])
    op.create_index("ix_messages_deleted_at", "messages", ["deleted_at"])

    op.create_table(
        "message_reads",
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("message_id", "user_id"),
    )
    op.create_index("ix_message_reads_user_id", "message_reads", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_message_reads_user_id", table_name="message_reads")
    op.drop_table("message_reads")
    op.drop_index("ix_messages_deleted_at", table_name="messages")
    op.drop_index("ix_messages_created_at", table_name="messages")
    op.drop_index("ix_messages_sender_id", table_name="messages")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_conversation_members_user_id", table_name="conversation_members")
    op.drop_table("conversation_members")
    op.drop_index("ix_conversations_type", table_name="conversations")
    op.drop_table("conversations")
    op.drop_index("ix_blocked_users_blocked_id", table_name="blocked_users")
    op.drop_index("ix_blocked_users_blocker_id", table_name="blocked_users")
    op.drop_table("blocked_users")
    op.drop_index("ix_friendships_user_b_id", table_name="friendships")
    op.drop_index("ix_friendships_user_a_id", table_name="friendships")
    op.drop_table("friendships")
    op.drop_index("ix_friend_requests_status", table_name="friend_requests")
    op.drop_index("ix_friend_requests_receiver_id", table_name="friend_requests")
    op.drop_index("ix_friend_requests_sender_id", table_name="friend_requests")
    op.drop_table("friend_requests")
