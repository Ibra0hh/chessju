"""admin audit logs

Revision ID: 0003_admin_audit_logs
Revises: 0002_auth_user_foundation
Create Date: 2026-05-19 00:00:03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_admin_audit_logs"
down_revision: str | None = "0002_auth_user_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "admin_action_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("admin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("before", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["admin_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_admin_action_logs_action", "admin_action_logs", ["action"])
    op.create_index("ix_admin_action_logs_admin_id", "admin_action_logs", ["admin_id"])
    op.create_index("ix_admin_action_logs_created_at", "admin_action_logs", ["created_at"])
    op.create_index("ix_admin_action_logs_entity_id", "admin_action_logs", ["entity_id"])
    op.create_index("ix_admin_action_logs_entity_type", "admin_action_logs", ["entity_type"])


def downgrade() -> None:
    op.drop_index("ix_admin_action_logs_entity_type", table_name="admin_action_logs")
    op.drop_index("ix_admin_action_logs_entity_id", table_name="admin_action_logs")
    op.drop_index("ix_admin_action_logs_created_at", table_name="admin_action_logs")
    op.drop_index("ix_admin_action_logs_admin_id", table_name="admin_action_logs")
    op.drop_index("ix_admin_action_logs_action", table_name="admin_action_logs")
    op.drop_table("admin_action_logs")
