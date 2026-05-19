"""auth user foundation

Revision ID: 0002_auth_user_foundation
Revises: 0001_initial_foundation
Create Date: 2026-05-19 00:00:02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_auth_user_foundation"
down_revision: str | None = "0001_initial_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ROLE_ROWS = [
    {"id": "00000000-0000-4000-8000-000000000001", "name": "member"},
    {"id": "00000000-0000-4000-8000-000000000002", "name": "arbiter"},
    {"id": "00000000-0000-4000-8000-000000000003", "name": "admin"},
    {"id": "00000000-0000-4000-8000-000000000004", "name": "super_admin"},
]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status in ('active', 'suspended', 'deleted')",
            name="ck_users_status_valid",
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_status", "users", ["status"])

    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=50), nullable=False),
    )
    op.create_index("ix_roles_name", "roles", ["name"], unique=True)

    roles_table = sa.table(
        "roles",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String()),
    )
    op.bulk_insert(roles_table, ROLE_ROWS)

    op.create_table(
        "profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("username", sa.String(length=40), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("university_id", sa.String(length=50), nullable=True),
        sa.Column("avatar_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("chesscom_username", sa.String(length=80), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_profiles_username", "profiles", ["username"], unique=True)
    op.create_unique_constraint("uq_profiles_user_id", "profiles", ["user_id"])

    op.create_table(
        "user_roles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
    )

    op.create_table(
        "user_preferences",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("app_theme", sa.String(length=30), nullable=False, server_default="system"),
        sa.Column("board_theme", sa.String(length=30), nullable=False, server_default="classic"),
        sa.Column("accent_color", sa.String(length=30), nullable=False, server_default="blue"),
        sa.Column("clock_sound_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column(
            "notification_settings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "privacy_settings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("replaced_by_token_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(
            ["replaced_by_token_id"], ["refresh_tokens.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_table("user_preferences")
    op.drop_table("user_roles")
    op.drop_constraint("uq_profiles_user_id", "profiles", type_="unique")
    op.drop_index("ix_profiles_username", table_name="profiles")
    op.drop_table("profiles")
    op.drop_index("ix_roles_name", table_name="roles")
    op.drop_table("roles")
    op.drop_index("ix_users_status", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
