"""Require one activity per planned workout.

Revision ID: 0006
Revises: 0005
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("activities") as batch_op:
        batch_op.create_unique_constraint(
            "uq_activities_planned_workout_id",
            ["planned_workout_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("activities") as batch_op:
        batch_op.drop_constraint(
            "uq_activities_planned_workout_id",
            type_="unique",
        )
