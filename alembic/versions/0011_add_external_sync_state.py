"""add external synchronization state

Revision ID: 0011
Revises: 0010
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("external_connections", sa.Column("sync_start_date", sa.Date(), nullable=True))
    op.add_column("external_connections", sa.Column("sync_enabled", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("external_connections", sa.Column("sync_status", sa.String(length=32), server_default="NOT_CONFIGURED", nullable=False))
    op.add_column("external_connections", sa.Column("sync_cursor_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("external_connections", sa.Column("sync_total", sa.Integer(), server_default="0", nullable=False))
    op.add_column("external_connections", sa.Column("sync_imported", sa.Integer(), server_default="0", nullable=False))
    op.add_column("external_connections", sa.Column("sync_skipped", sa.Integer(), server_default="0", nullable=False))
    op.add_column("external_connections", sa.Column("sync_failed", sa.Integer(), server_default="0", nullable=False))
    op.add_column("external_connections", sa.Column("sync_last_error", sa.String(length=1000), nullable=True))


def downgrade() -> None:
    for column in (
        "sync_last_error",
        "sync_failed",
        "sync_skipped",
        "sync_imported",
        "sync_total",
        "sync_cursor_at",
        "sync_status",
        "sync_enabled",
        "sync_start_date",
    ):
        op.drop_column("external_connections", column)
