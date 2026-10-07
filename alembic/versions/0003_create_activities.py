"""create activities

Revision ID: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "activities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sport", sa.String(length=32), nullable=False),
        sa.Column("duration_minutes", sa.Float(), nullable=False),
        sa.Column("distance_km", sa.Float(), nullable=True),
        sa.Column("average_power", sa.Float(), nullable=True),
        sa.Column("normalized_power", sa.Float(), nullable=True),
        sa.Column("average_heart_rate", sa.Float(), nullable=True),
        sa.Column("intensity_factor", sa.Float(), nullable=True),
        sa.Column("tss", sa.Float(), nullable=True),
        sa.Column("aerobic_decoupling", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("external_source_id", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.String(length=4000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_activities_user_id", "activities", ["user_id"])
    op.create_index("ix_activities_started_at", "activities", ["started_at"])
    op.create_index("ix_activities_user_started_at", "activities", ["user_id", "started_at"])


def downgrade() -> None:
    op.drop_index("ix_activities_user_started_at", table_name="activities")
    op.drop_index("ix_activities_started_at", table_name="activities")
    op.drop_index("ix_activities_user_id", table_name="activities")
    op.drop_table("activities")
