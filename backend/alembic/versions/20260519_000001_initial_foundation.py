"""initial foundation

Revision ID: 0001_initial_foundation
Revises:
Create Date: 2026-05-19 00:00:01
"""

from collections.abc import Sequence

revision: str = "0001_initial_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
