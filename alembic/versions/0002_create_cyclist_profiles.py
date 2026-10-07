"""create cyclist profiles

Revision ID: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cyclist_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("ftp", sa.Float(), nullable=False),
        sa.Column("weekly_hours", sa.Float(), nullable=False),
        sa.Column("available_days", sa.JSON(), nullable=False),
        sa.Column("modality", sa.String(length=32), nullable=False),
        sa.Column("level", sa.String(length=32), nullable=False),
        sa.Column("objective", sa.String(length=32), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_cyclist_profiles_user_id", "cyclist_profiles", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_cyclist_profiles_user_id", table_name="cyclist_profiles")
    op.drop_table("cyclist_profiles")
