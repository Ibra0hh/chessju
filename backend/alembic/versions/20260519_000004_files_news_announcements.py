"""files news announcements

Revision ID: 0004_files_news_announcements
Revises: 0003_admin_audit_logs
Create Date: 2026-05-19 00:00:04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_files_news_announcements"
down_revision: str | None = "0003_admin_audit_logs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("file_type", sa.Text(), nullable=False),
        sa.Column("storage_provider", sa.Text(), nullable=False, server_default="local"),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "file_type in ('avatar', 'news_image', 'tournament_image', 'pgn', 'export', 'other')",
            name="ck_files_file_type_valid",
        ),
        sa.CheckConstraint(
            "storage_provider in ('local')",
            name="ck_files_storage_provider_valid",
        ),
        sa.CheckConstraint("size_bytes >= 0", name="ck_files_size_bytes_non_negative"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_files_owner_id", "files", ["owner_id"])
    op.create_index("ix_files_file_type", "files", ["file_type"])

    op.create_table(
        "articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("body_markdown", sa.Text(), nullable=False),
        sa.Column("cover_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status in ('draft', 'published', 'archived')",
            name="ck_articles_status_valid",
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cover_file_id"], ["files.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_articles_slug", "articles", ["slug"], unique=True)
    op.create_index("ix_articles_status", "articles", ["status"])
    op.create_index("ix_articles_published_at", "articles", ["published_at"])
    op.create_index("ix_articles_deleted_at", "articles", ["deleted_at"])

    op.create_table(
        "announcements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("target", sa.Text(), nullable=False, server_default="all"),
        sa.Column("priority", sa.Text(), nullable=False, server_default="normal"),
        sa.Column("status", sa.Text(), nullable=False, server_default="published"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "target in ('all', 'members', 'admins', 'tournament_players')",
            name="ck_announcements_target_valid",
        ),
        sa.CheckConstraint(
            "priority in ('normal', 'important', 'urgent')",
            name="ck_announcements_priority_valid",
        ),
        sa.CheckConstraint(
            "status in ('draft', 'published', 'archived')",
            name="ck_announcements_status_valid",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_announcements_status", "announcements", ["status"])
    op.create_index("ix_announcements_published_at", "announcements", ["published_at"])
    op.create_index("ix_announcements_expires_at", "announcements", ["expires_at"])
    op.create_index("ix_announcements_deleted_at", "announcements", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_announcements_deleted_at", table_name="announcements")
    op.drop_index("ix_announcements_expires_at", table_name="announcements")
    op.drop_index("ix_announcements_published_at", table_name="announcements")
    op.drop_index("ix_announcements_status", table_name="announcements")
    op.drop_table("announcements")
    op.drop_index("ix_articles_deleted_at", table_name="articles")
    op.drop_index("ix_articles_published_at", table_name="articles")
    op.drop_index("ix_articles_status", table_name="articles")
    op.drop_index("ix_articles_slug", table_name="articles")
    op.drop_table("articles")
    op.drop_index("ix_files_file_type", table_name="files")
    op.drop_index("ix_files_owner_id", table_name="files")
    op.drop_table("files")
