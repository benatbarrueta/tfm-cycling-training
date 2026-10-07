"""create season plan persistence

Revision ID: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "season_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("objective", sa.String(32), nullable=False),
        sa.Column("modality", sa.String(32), nullable=False),
        sa.Column("level", sa.String(32), nullable=False),
        sa.Column("ftp_snapshot", sa.Float(), nullable=False),
        sa.Column("weekly_hours_snapshot", sa.Float(), nullable=False),
        sa.Column("available_days_snapshot", sa.JSON(), nullable=False),
        sa.Column("generator_version", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_season_plans_user_id", "season_plans", ["user_id"])
    op.create_index("ix_season_plans_user_status", "season_plans", ["user_id", "status"])

    op.create_table(
        "training_phases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("season_plan_id", sa.Uuid(), nullable=False),
        sa.Column("phase_type", sa.String(32), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("week_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["season_plan_id"], ["season_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_training_phases_season_plan_id", "training_phases", ["season_plan_id"])

    op.create_table(
        "planned_weeks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("season_plan_id", sa.Uuid(), nullable=False),
        sa.Column("training_phase_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("week_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("focus", sa.String(64), nullable=False),
        sa.Column("provisional_target_tss", sa.Float(), nullable=False),
        sa.Column("provisional_hours", sa.Float(), nullable=False),
        sa.Column("requested_target_tss", sa.Float(), nullable=True),
        sa.Column("adapted_target_tss", sa.Float(), nullable=True),
        sa.Column("estimated_total_tss", sa.Float(), nullable=True),
        sa.Column("expected_aerobic_decoupling", sa.Float(), nullable=True),
        sa.Column("response_prediction_method", sa.String(64), nullable=True),
        sa.Column("load_decision", sa.String(32), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["season_plan_id"], ["season_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["training_phase_id"], ["training_phases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_planned_weeks_season_plan_id", "planned_weeks", ["season_plan_id"])
    op.create_index("ix_planned_weeks_training_phase_id", "planned_weeks", ["training_phase_id"])

    op.create_table(
        "planned_workouts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("planned_week_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("day", sa.String(16), nullable=False),
        sa.Column("workout_type", sa.String(32), nullable=False),
        sa.Column("target_tss", sa.Float(), nullable=False),
        sa.Column("estimated_tss", sa.Float(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("target_power_min", sa.Float(), nullable=True),
        sa.Column("target_power_max", sa.Float(), nullable=True),
        sa.Column("warmup", sa.JSON(), nullable=True),
        sa.Column("intervals", sa.JSON(), nullable=True),
        sa.Column("cooldown", sa.JSON(), nullable=True),
        sa.Column("predicted_aerobic_decoupling", sa.Float(), nullable=True),
        sa.Column("aerobic_response", sa.String(32), nullable=True),
        sa.Column("outside_training_range_features", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["planned_week_id"], ["planned_weeks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_planned_workouts_planned_week_id", "planned_workouts", ["planned_week_id"])


def downgrade() -> None:
    op.drop_index("ix_planned_workouts_planned_week_id", table_name="planned_workouts")
    op.drop_table("planned_workouts")
    op.drop_index("ix_planned_weeks_training_phase_id", table_name="planned_weeks")
    op.drop_index("ix_planned_weeks_season_plan_id", table_name="planned_weeks")
    op.drop_table("planned_weeks")
    op.drop_index("ix_training_phases_season_plan_id", table_name="training_phases")
    op.drop_table("training_phases")
    op.drop_index("ix_season_plans_user_status", table_name="season_plans")
    op.drop_index("ix_season_plans_user_id", table_name="season_plans")
    op.drop_table("season_plans")
