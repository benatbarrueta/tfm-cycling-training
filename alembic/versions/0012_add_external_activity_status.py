"""add external activity status

Revision ID: 0012
Revises: 0011
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "activities",
        sa.Column("external_status", sa.String(length=32), server_default="ACTIVE", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("activities", "external_status")
