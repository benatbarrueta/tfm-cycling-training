"""add Strava reconciliation state

Revision ID: 0013
Revises: 0012
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("external_connections", sa.Column("last_sync_attempt_at", sa.DateTime(timezone=True)))
    for name in (
        "last_sync_new",
        "last_sync_updated",
        "last_sync_deleted",
        "last_sync_unchanged",
        "last_sync_failed",
    ):
        op.add_column(
            "external_connections",
            sa.Column(name, sa.Integer(), server_default="0", nullable=False),
        )


def downgrade() -> None:
    for name in (
        "last_sync_failed",
        "last_sync_unchanged",
        "last_sync_deleted",
        "last_sync_updated",
        "last_sync_new",
    ):
        op.drop_column("external_connections", name)
    op.drop_column("external_connections", "last_sync_attempt_at")
