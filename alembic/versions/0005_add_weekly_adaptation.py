"""add workout links and weekly adaptation audit

Revision ID: 0005
"""

from alembic import op
import sqlalchemy as sa


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("activities") as batch:
        batch.add_column(sa.Column("planned_workout_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            "fk_activities_planned_workout_id",
            "planned_workouts",
            ["planned_workout_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_index("ix_activities_planned_workout_id", ["planned_workout_id"])

    op.create_table(
        "weekly_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("planned_week_id", sa.Uuid(), nullable=False),
        sa.Column("planned_tss", sa.Float(), nullable=False),
        sa.Column("registered_tss", sa.Float(), nullable=False),
        sa.Column("tss_coverage", sa.Float(), nullable=False),
        sa.Column("planned_duration_minutes", sa.Float(), nullable=False),
        sa.Column("registered_duration_minutes", sa.Float(), nullable=False),
        sa.Column("planned_workout_count", sa.Integer(), nullable=False),
        sa.Column("completed_workout_count", sa.Integer(), nullable=False),
        sa.Column("activity_count", sa.Integer(), nullable=False),
        sa.Column("activities_with_tss", sa.Integer(), nullable=False),
        sa.Column("activities_without_tss", sa.Integer(), nullable=False),
        sa.Column("response_median", sa.Float(), nullable=True),
        sa.Column("response_count", sa.Integer(), nullable=False),
        sa.Column("load_decision", sa.String(32), nullable=True),
        sa.Column("decision_reason", sa.String(1000), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["planned_week_id"], ["planned_weeks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("planned_week_id"),
    )
    op.create_index("ix_weekly_reviews_planned_week_id", "weekly_reviews", ["planned_week_id"])

    op.create_table(
        "adaptation_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("season_plan_id", sa.Uuid(), nullable=False),
        sa.Column("source_week_id", sa.Uuid(), nullable=False),
        sa.Column("target_week_id", sa.Uuid(), nullable=True),
        sa.Column("previous_target_tss", sa.Float(), nullable=False),
        sa.Column("provisional_target_tss", sa.Float(), nullable=True),
        sa.Column("adapted_target_tss", sa.Float(), nullable=True),
        sa.Column("load_decision", sa.String(32), nullable=True),
        sa.Column("observed_aerobic_decoupling", sa.Float(), nullable=True),
        sa.Column("response_classification", sa.String(32), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column("rule_version", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["season_plan_id"], ["season_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_week_id"], ["planned_weeks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_week_id"], ["planned_weeks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_week_id", name="uq_adaptation_events_source_week"),
    )
    op.create_index("ix_adaptation_events_season_plan_id", "adaptation_events", ["season_plan_id"])
    op.create_index("ix_adaptation_events_source_week_id", "adaptation_events", ["source_week_id"])
    op.create_index("ix_adaptation_events_target_week_id", "adaptation_events", ["target_week_id"])


def downgrade() -> None:
    op.drop_index("ix_adaptation_events_target_week_id", table_name="adaptation_events")
    op.drop_index("ix_adaptation_events_source_week_id", table_name="adaptation_events")
    op.drop_index("ix_adaptation_events_season_plan_id", table_name="adaptation_events")
    op.drop_table("adaptation_events")
    op.drop_index("ix_weekly_reviews_planned_week_id", table_name="weekly_reviews")
    op.drop_table("weekly_reviews")
    with op.batch_alter_table("activities") as batch:
        batch.drop_index("ix_activities_planned_workout_id")
        batch.drop_constraint("fk_activities_planned_workout_id", type_="foreignkey")
        batch.drop_column("planned_workout_id")
